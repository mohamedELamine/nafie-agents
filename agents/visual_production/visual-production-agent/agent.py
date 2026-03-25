"""
Visual-production-agent pipeline.

Pipeline order:
  1.  contract_parser     — extract domain/cluster/colors/features
  2.  budget_calculator   — reject if estimated cost > limit
  3.  prompt_builder      — build PromptBundle per asset type
  4.  multi_generator     — parallel image generation (Flux / Ideogram)
  5.  quality_gate        — reject low-quality images
  6.  asset_selector      — verify minimum viable set
  7.  post_processor      — resize / compress / watermark
  8.  review_gate         — save checkpoint + send email for human review
  ── HUMAN REVIEW ──
  9.  asset_publisher     — upload approved assets to storage (after approval)
  10. batch_recorder      — save batch log + manifest
  11. manifest_builder    — build final JSON + publish THEME_ASSETS_READY
"""
import os
from typing import Any, Dict

from .logging_config import get_logger
from .models import AssetType, PromptBundle
from .nodes import (
    ContractParserNode,
    BudgetCalculatorNode,
    PromptBuilderNode,
    MultiGeneratorNode,
    QualityGateNode,
    AssetSelectorNode,
    PostProcessorNode,
    ReviewGateNode,
    AssetPublisherNode,
    BatchRecorderNode,
    ManifestBuilderNode,
)

logger = get_logger("visual_production.agent")


def _auto_approve_review() -> bool:
    return os.environ.get("VISUAL_AUTO_APPROVE_REVIEW", "").lower() in {"1", "true", "yes", "on"}


# ---------------------------------------------------------------------------
# Data class holding all node instances for a running pipeline
# ---------------------------------------------------------------------------

class VisualAgent:
    def __init__(
        self,
        flux_client,
        ideogram_client,
        image_processor,
        storage_client,
        redis_bus,
        resend_client,
        budget_limit: float = 2.00,
    ):
        self.flux = flux_client
        self.ideogram = ideogram_client
        self.processor = image_processor
        self.storage = storage_client
        self.redis = redis_bus
        self.resend = resend_client
        self.budget_limit = budget_limit

        self.contract_parser   = ContractParserNode()
        self.budget_calculator = BudgetCalculatorNode(budget_limit=budget_limit)
        self.prompt_builder    = PromptBuilderNode()
        self.multi_generator   = MultiGeneratorNode(flux_client, ideogram_client)
        self.quality_gate      = QualityGateNode(image_processor)
        self.asset_selector    = AssetSelectorNode()
        self.post_processor    = PostProcessorNode(image_processor)
        self.review_gate       = ReviewGateNode(resend_client, redis_bus)
        self.asset_publisher   = AssetPublisherNode(storage_client)
        self.batch_recorder    = BatchRecorderNode()
        self.manifest_builder  = ManifestBuilderNode(redis_bus)


def build_visual_agent() -> VisualAgent:
    """Construct VisualAgent from environment / service factories."""
    from .services import (
        get_flux_client,
        get_ideogram_client,
        get_image_processor,
        get_storage_client,
        get_redis_bus,
        get_resend_client,
    )

    return VisualAgent(
        flux_client=get_flux_client(),
        ideogram_client=get_ideogram_client(),
        image_processor=get_image_processor(),
        storage_client=get_storage_client(),
        redis_bus=get_redis_bus(),
        resend_client=get_resend_client(),
        budget_limit=float(os.environ.get("VISUAL_BUDGET_LIMIT", "2.00")),
    )


# ---------------------------------------------------------------------------
# Pipeline runner
# ---------------------------------------------------------------------------

async def run_visual_pipeline(
    agent: VisualAgent,
    theme_contract: Dict[str, Any],
    batch_id: str,
    version: str,
    owner_email: str,
) -> Dict[str, Any]:
    """Run the complete visual production pipeline.

    Steps 1-8 run on every call and end with a human review checkpoint.
    Steps 9-11 are invoked only when the reviewer approves the batch
    (via the /review/{batch_id} endpoint).
    """
    logger.info(f"Starting visual pipeline for batch {batch_id}")

    # Step 1: Parse contract
    parsed = agent.contract_parser(theme_contract)

    # Step 2: Budget guard
    cost_estimate = 0.08 * 4  # 4 asset types × base cost
    budget_result = agent.budget_calculator(cost_estimate)
    if budget_result["rejected"]:
        logger.error(f"Budget exceeded for batch {batch_id}: {budget_result}")
        return {
            "status": "budget_rejected",
            "reason": budget_result["reason"],
            "estimated_cost": budget_result["estimated_cost"],
        }

    # Step 3: Build prompts
    prompt_bundles: Dict[str, PromptBundle] = {}
    for asset_type in [
        AssetType.HERO_IMAGE,
        AssetType.PRODUCT_CARD,
        AssetType.SCREENSHOT_HOME,
        AssetType.SCREENSHOT_INNER,
    ]:
        pb = agent.prompt_builder(
            domain=parsed["domain"],
            cluster=parsed["cluster"],
            colors=parsed["colors"],
            features=parsed["features"],
            asset_type=asset_type,
        )
        prompt_bundles[asset_type] = PromptBundle(
            asset_type=asset_type,
            positive_prompt=pb["prompt"],
            negative_prompt=pb["negative_prompt"],
            dimensions=(1920, 1080) if asset_type != AssetType.PRODUCT_CARD else (800, 600),
            generator="flux" if asset_type != AssetType.PRODUCT_CARD else "ideogram",
        )

    # Step 4: Generate assets (parallel)
    generation_result = await agent.multi_generator(prompt_bundles)
    generated_assets = generation_result["generated"]
    if not generated_assets:
        return {"status": "failed", "reason": "No assets generated", "batch_id": batch_id}

    # Step 5: Quality gate
    quality_result = agent.quality_gate(generated_assets)
    if quality_result["approved_count"] == 0:
        return {
            "status": "failed",
            "reason": "No assets passed quality gate",
            "batch_id": batch_id,
        }

    # Step 6: Asset selection
    selection_result = agent.asset_selector(quality_result["approved"])
    if not selection_result["complete"]:
        return {
            "status": "incomplete",
            "reason": "Minimum viable set incomplete",
            "missing": selection_result["missing"],
            "batch_id": batch_id,
        }

    # Step 7: Post-processing
    processed_result = agent.post_processor(selection_result["selected"])

    # Step 8: Review gate — save checkpoint + notify owner
    review_result = await agent.review_gate(
        processed_assets=processed_result,
        batch_id=batch_id,
        theme_slug=theme_contract.get("slug", ""),
        version=version,
        owner_email=owner_email,
    )

    logger.info(
        f"Visual pipeline paused at review_gate for batch {batch_id} "
        f"— awaiting human approval"
    )

    if _auto_approve_review():
        logger.info("VISUAL_AUTO_APPROVE_REVIEW enabled; completing batch %s automatically", batch_id)
        approved_result = await complete_approved_pipeline(
            agent=agent,
            batch_id=batch_id,
            theme_slug=theme_contract.get("slug", ""),
            version=version,
            processed_result=processed_result,
            owner_email=owner_email,
        )
        await agent.redis.checkpoint_delete(f"visual_review:{batch_id}")
        return approved_result

    return {
        "status": review_result["status"],   # "review_pending"
        "batch_id": batch_id,
        "assets_count": review_result["assets_count"],
    }


async def complete_approved_pipeline(
    agent: VisualAgent,
    batch_id: str,
    theme_slug: str,
    version: str,
    processed_result: Dict[str, Any],
    owner_email: str = "",
) -> Dict[str, Any]:
    """
    Continue the pipeline after human approval.
    Called from the /review/{batch_id} webhook when decision == "approved".
    """
    logger.info(f"Continuing pipeline after approval — batch {batch_id}")

    # Step 9: Publish assets to storage
    publish_result = await agent.asset_publisher(
        processed_assets=processed_result, batch_id=batch_id
    )

    # Step 10: Record batch in DB
    await agent.batch_recorder(
        batch_id=batch_id,
        theme_slug=theme_slug,
        version=version,
        total_cost=0.08 * len(publish_result["assets"]),
        assets=publish_result["assets"],
        status="published",
    )

    # Step 11: Build manifest + emit THEME_ASSETS_READY event
    final_result = await agent.manifest_builder(
        batch_id=batch_id,
        theme_slug=theme_slug,
        approved_assets={"assets": publish_result["assets"]},
    )

    if owner_email:
        await agent.resend.send_batch_complete(
            to_email=owner_email,
            batch_id=batch_id,
            theme_slug=theme_slug,
            approved_count=len(publish_result["assets"]),
            rejected_count=0,
        )

    logger.info(f"Visual pipeline completed — batch {batch_id}")
    return final_result
