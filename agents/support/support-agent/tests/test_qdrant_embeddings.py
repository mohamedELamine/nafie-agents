import importlib.util
import logging
import pathlib
import sys
import types

AGENT_ROOT = pathlib.Path(__file__).resolve().parents[1]


def _load_module(name: str, path: pathlib.Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _install_qdrant_stubs():
    package = types.ModuleType("support_agent")
    package.__path__ = [str(AGENT_ROOT)]
    services_package = types.ModuleType("support_agent.services")
    services_package.__path__ = [str(AGENT_ROOT / "services")]
    logging_module = types.ModuleType("support_agent.logging_config")
    logging_module.get_logger = lambda name: logging.getLogger(name)

    qdrant_module = types.ModuleType("qdrant_client")
    qdrant_models = types.ModuleType("qdrant_client.models")
    httpx_module = types.ModuleType("httpx")

    class ExternalQdrantClient:
        def __init__(self, url: str):
            self.url = url

        def collection_exists(self, name: str) -> bool:
            return True

        def create_collection(self, **kwargs):
            return None

        def search(self, **kwargs):
            return []

        def upsert(self, **kwargs):
            return None

    class Filter:
        def __init__(self, must=None):
            self.must = must or []

    class FieldCondition:
        def __init__(self, key, match):
            self.key = key
            self.match = match

    class MatchValue:
        def __init__(self, value):
            self.value = value

    qdrant_module.QdrantClient = ExternalQdrantClient
    qdrant_models.Filter = Filter
    qdrant_models.FieldCondition = FieldCondition
    qdrant_models.MatchValue = MatchValue

    sys.modules["support_agent"] = package
    sys.modules["support_agent.services"] = services_package
    sys.modules["support_agent.logging_config"] = logging_module
    sys.modules["qdrant_client"] = qdrant_module
    sys.modules["qdrant_client.models"] = qdrant_models
    sys.modules["httpx"] = httpx_module


def test_qdrant_client_uses_openai_compatible_embeddings_when_configured():
    _install_qdrant_stubs()
    module = _load_module(
        "support_agent.services.qdrant_client",
        AGENT_ROOT / "services" / "qdrant_client.py",
    )

    class _Response:
        def raise_for_status(self):
            return None

        def json(self):
            return {"data": [{"embedding": [0.1, 0.2, 0.3]}]}

    module.httpx.post = lambda *args, **kwargs: _Response()

    client = module.QdrantClient("http://localhost:6333")
    client.embedding_provider = "openai"
    client.embedding_api_key = "sk-test"

    embedding = client._encode_text("license activation issue")

    assert embedding == [0.1, 0.2, 0.3]
    assert client.vector_size == 3
