from types import SimpleNamespace
from unittest.mock import MagicMock


def test_parser_extracts_sections_from_event(
    platform_env: SimpleNamespace,
    sample_product_event,
) -> None:
    module = platform_env.load_module(
        "platform_contract_parser_under_test",
        platform_env.agent_dir / "nodes" / "launch" / "contract_parser.py",
    )
    registry = SimpleNamespace(db=MagicMock())

    result = module.make_contract_parser_node(registry)(sample_product_event)

    assert result["parsed"]["theme_name_ar"] == "قالب تجريبي"
    assert "woocommerce_features" in result["parsed"]["required_sections"]
    assert "cod_features" in result["parsed"]["required_sections"]


def test_parser_handles_missing_fields_without_exception(
    platform_env: SimpleNamespace,
    sample_product_event,
) -> None:
    module = platform_env.load_module(
        "platform_contract_parser_under_test_missing",
        platform_env.agent_dir / "nodes" / "launch" / "contract_parser.py",
    )
    registry = SimpleNamespace(db=MagicMock())
    state = dict(sample_product_event)
    state["theme_contract"] = {}

    result = module.make_contract_parser_node(registry)(state)

    assert result["parsed"]["theme_name_ar"] == "theme-one"
    assert result["parsed"]["domain"] == "general"
    assert result["parsed"]["build_version"] == "1.0.0"
