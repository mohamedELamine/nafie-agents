"""
Node: CONTRACT_PARSER — T042
يفك theme_contract ويستخرج البيانات اللازمة لبقية الـ workflow.
"""
from __future__ import annotations
import logging
from db.idempotency import check_completed, mark_completed, mark_started
from db.registry import ProductRegistry
from state import LaunchState, PlatformStatus

logger = logging.getLogger("platform_agent.nodes.launch.contract_parser")
NODE_NAME = "CONTRACT_PARSER"
MANDATORY_SECTIONS = ["hero","features","target_audience","quality_section","pricing_section","faq","cta"]

def make_contract_parser_node(registry: ProductRegistry):
    def contract_parser_node(state: LaunchState) -> dict:
        ikey = state["idempotency_key"]
        if check_completed(registry.db, ikey, NODE_NAME):
            return state
        mark_started(registry.db, ikey, NODE_NAME)
        contract = state.get("theme_contract", {})
        woo = contract.get("woocommerce_enabled", False)
        cod = contract.get("cod_enabled", False)
        sections = list(MANDATORY_SECTIONS)
        if woo: sections.append("woocommerce_features")
        if cod: sections.append("cod_features")
        parsed = {
            "theme_name_ar": contract.get("theme_name_ar", state["theme_slug"]),
            "domain": contract.get("domain", "general"),
            "cluster": contract.get("cluster", "ecommerce"),
            "build_version": contract.get("build_version", state.get("version","1.0.0")),
            "woocommerce_enabled": woo,
            "cod_enabled": cod,
            "required_sections": sections,
        }
        result = {**state, "parsed": parsed,
                  "logs": state.get("logs",[]) + [f"CONTRACT_PARSER: sections={sections}"]}
        mark_completed(registry.db, ikey, NODE_NAME, result)
        logger.info("CONTRACT_PARSER | DONE | theme=%s", state["theme_slug"])
        return result
    return contract_parser_node
