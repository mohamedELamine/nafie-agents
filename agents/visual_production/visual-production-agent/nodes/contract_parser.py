from typing import Dict, Any
import logging

logger = logging.getLogger("visual_production.contract_parser")


class ContractParserNode:
    def __call__(self, theme_contract: Dict[str, Any]) -> Dict[str, Any]:
        """Extract domain, cluster, colors, features from theme contract"""
        return {
            "domain": theme_contract.get("domain", ""),
            "cluster": theme_contract.get("cluster", ""),
            "colors": theme_contract.get("colors", []),
            "features": theme_contract.get("features", []),
            "woo_enabled": theme_contract.get("woocommerce_enabled", False),
            "cod_enabled": theme_contract.get("cod_enabled", False),
        }


contract_parser_node = ContractParserNode()
