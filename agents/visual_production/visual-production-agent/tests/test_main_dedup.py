import asyncio
import importlib.util
import pathlib
import sys
from types import ModuleType
from unittest.mock import AsyncMock


AGENT_ROOT = pathlib.Path(__file__).resolve().parents[1]
PROJECT_ROOT = AGENT_ROOT.parents[3]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def _load_module(name: str, path: pathlib.Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_handle_event_deduplicates_same_launch_across_product_events() -> None:
    visual_main = _load_module("visual_main_dedup_test", AGENT_ROOT / "main.py")
    visual_main._recent_launches.clear()
    runner = AsyncMock(return_value={"status": "published"})
    original_runner = visual_main.run_visual_pipeline
    visual_main.run_visual_pipeline = runner

    try:
        asyncio.run(
            visual_main._handle_event(
                agent=object(),
                event={
                    "event_type": visual_main.EVENT_THEME_APPROVED,
                    "data": {"theme_slug": "theme-one", "version": "1.0.0"},
                },
            )
        )
        asyncio.run(
            visual_main._handle_event(
                agent=object(),
                event={
                    "event_type": visual_main.EVENT_NEW_PRODUCT_LIVE,
                    "data": {"theme_slug": "theme-one", "version": "1.0.0"},
                },
            )
        )
    finally:
        visual_main.run_visual_pipeline = original_runner
        visual_main._recent_launches.clear()

    assert runner.await_count == 1
    assert runner.await_args.kwargs["theme_contract"]["slug"] == "theme-one"
    assert runner.await_args.kwargs["theme_contract"]["version"] == "1.0.0"
