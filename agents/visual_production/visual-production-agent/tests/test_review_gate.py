import asyncio
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock


def test_review_gate_saves_checkpoint_and_returns_pending(
    visual_env: SimpleNamespace,
    mock_get_conn,
    sample_batch_state,
) -> None:
    module = visual_env.load_module(
        "visual_production_agent.nodes.review_gate",
        visual_env.agent_dir / "nodes" / "review_gate.py",
    )
    module.get_conn = mock_get_conn
    redis_bus = MagicMock()
    redis_bus.checkpoint_save = AsyncMock(return_value=True)
    resend = MagicMock()
    resend.send_visual_review_request = AsyncMock(return_value=True)

    result = asyncio.run(
        module.ReviewGateNode(resend, redis_bus)(
            processed_assets=sample_batch_state["processed_assets"],
            batch_id=sample_batch_state["batch_id"],
            theme_slug=sample_batch_state["theme_slug"],
            version=sample_batch_state["version"],
            owner_email=sample_batch_state["owner_email"],
        )
    )

    assert result["status"] == "review_pending"
    redis_bus.checkpoint_save.assert_awaited_once()
    resend.send_visual_review_request.assert_awaited_once()


def test_review_gate_persists_timezone_aware_created_at(
    visual_env: SimpleNamespace,
    mock_get_conn,
    sample_batch_state,
) -> None:
    module = visual_env.load_module(
        "visual_production_agent.nodes.review_gate",
        visual_env.agent_dir / "nodes" / "review_gate.py",
    )
    module.get_conn = mock_get_conn
    redis_bus = MagicMock()
    redis_bus.checkpoint_save = AsyncMock(return_value=True)
    resend = MagicMock()
    resend.send_visual_review_request = AsyncMock(return_value=True)

    asyncio.run(
        module.ReviewGateNode(resend, redis_bus)(
            processed_assets=sample_batch_state["processed_assets"],
            batch_id=sample_batch_state["batch_id"],
            theme_slug=sample_batch_state["theme_slug"],
            version=sample_batch_state["version"],
            owner_email=sample_batch_state["owner_email"],
        )
    )

    manifest = visual_env.db.save_manifest.call_args.args[1]
    created_at = datetime.fromisoformat(manifest["created_at"])
    assert created_at.tzinfo == timezone.utc
