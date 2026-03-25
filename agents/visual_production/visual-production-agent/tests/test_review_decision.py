import asyncio
import importlib.util
import logging
import pathlib
import sys
import types
from contextlib import contextmanager

AGENT_ROOT = pathlib.Path(__file__).resolve().parents[1]


def _load_module(name: str, path: pathlib.Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _install_fastapi_stubs():
    fastapi = types.ModuleType("fastapi")

    class HTTPException(Exception):
        def __init__(self, status_code: int, detail):
            super().__init__(detail)
            self.status_code = status_code
            self.detail = detail

    class FastAPI:
        def __init__(self, *args, **kwargs):
            self.args = args
            self.kwargs = kwargs

        def add_middleware(self, *args, **kwargs):
            return None

        def get(self, *args, **kwargs):
            return lambda fn: fn

        def post(self, *args, **kwargs):
            return lambda fn: fn

        def middleware(self, *args, **kwargs):
            return lambda fn: fn

        def exception_handler(self, *args, **kwargs):
            return lambda fn: fn

    fastapi.FastAPI = FastAPI
    fastapi.HTTPException = HTTPException
    fastapi.Request = object

    cors_module = types.ModuleType("fastapi.middleware.cors")
    cors_module.CORSMiddleware = object

    responses_module = types.ModuleType("fastapi.responses")
    responses_module.JSONResponse = dict

    sys.modules["fastapi"] = fastapi
    sys.modules["fastapi.middleware.cors"] = cors_module
    sys.modules["fastapi.responses"] = responses_module


def _install_supporting_stubs():
    db_module = types.ModuleType("db")
    db_module.update_calls = []

    @contextmanager
    def get_conn():
        yield object()

    def update_manifest_status(conn, batch_id, status, notes=None):
        db_module.update_calls.append((batch_id, status, notes))

    db_module.get_conn = get_conn
    db_module.get_manifest = lambda conn, batch_id: None
    db_module.init_pool = lambda: None
    db_module.close_pool = lambda: None
    db_module.update_manifest_status = update_manifest_status
    sys.modules["db"] = db_module

    logging_config = types.ModuleType("logging_config")
    logging_config.get_logger = lambda name: logging.getLogger(name)
    sys.modules["logging_config"] = logging_config

    agent_module = types.ModuleType("agent")
    sys.modules["agent"] = agent_module
    visual_pkg = types.ModuleType("visual_production_agent")
    visual_pkg.__path__ = [str(AGENT_ROOT)]
    visual_pkg.__package__ = "visual_production_agent"
    sys.modules["visual_production_agent"] = visual_pkg
    sys.modules["visual_production_agent.agent"] = agent_module
    return db_module, agent_module


def _load_api_module():
    _install_fastapi_stubs()
    db_module, agent_module = _install_supporting_stubs()
    api_module = _load_module(
        "visual_api_under_test",
        AGENT_ROOT / "api" / "main.py",
    )
    return api_module, db_module, agent_module


class _FakeRedis:
    def __init__(self, checkpoint):
        self.checkpoint = checkpoint
        self.deleted = []

    async def checkpoint_get(self, key):
        return self.checkpoint

    async def checkpoint_delete(self, key):
        self.deleted.append(key)
        return True


def test_handle_review_decision_approved_completes_pipeline():
    api_module, _, agent_module = _load_api_module()
    fake_redis = _FakeRedis(
        {
            "theme_slug": "theme-one",
            "version": "1.2.0",
            "owner_email": "owner@example.com",
            "assets": {"hero": {"size_kb": 42}},
            "total_size_kb": 42,
        }
    )
    fake_agent = types.SimpleNamespace(redis=fake_redis, resend=object())
    pipeline_calls = {}

    async def complete_approved_pipeline(**kwargs):
        pipeline_calls.update(kwargs)
        return {"status": "published", "assets_count": 1}

    agent_module.build_visual_agent = lambda: fake_agent
    agent_module.complete_approved_pipeline = complete_approved_pipeline

    result = asyncio.run(
        api_module.handle_review_decision("batch_1", {"decision": "approved"})
    )

    assert result["status"] == "approved"
    assert result["result"]["status"] == "published"
    assert fake_redis.deleted == ["visual_review:batch_1"]
    assert pipeline_calls["theme_slug"] == "theme-one"
    assert pipeline_calls["owner_email"] == "owner@example.com"


def test_handle_review_decision_rejected_updates_manifest_and_clears_checkpoint():
    api_module, db_module, agent_module = _load_api_module()
    fake_redis = _FakeRedis({"theme_slug": "theme-two"})
    fake_agent = types.SimpleNamespace(redis=fake_redis, resend=object())

    async def complete_approved_pipeline(**kwargs):
        raise AssertionError("approval pipeline should not run for rejected batches")

    agent_module.build_visual_agent = lambda: fake_agent
    agent_module.complete_approved_pipeline = complete_approved_pipeline

    result = asyncio.run(
        api_module.handle_review_decision(
            "batch_2",
            {"decision": "rejected", "notes": "artifacts remained visible"},
        )
    )

    assert result["status"] == "rejected"
    assert db_module.update_calls == [
        ("batch_2", "rejected", "artifacts remained visible")
    ]
    assert fake_redis.deleted == ["visual_review:batch_2"]
