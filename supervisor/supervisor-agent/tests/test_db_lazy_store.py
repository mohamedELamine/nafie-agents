import importlib.util
import os
import pathlib
import sys
import types


SUPERVISOR_ROOT = pathlib.Path(__file__).resolve().parents[1]


def _module(name: str, **attrs):
    module = types.ModuleType(name)
    for key, value in attrs.items():
        setattr(module, key, value)
    sys.modules[name] = module
    return module


def _load_module(name: str, path: pathlib.Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_health_store_import_is_lazy_without_database_url():
    os.environ.pop("DATABASE_URL", None)
    sys.path.insert(0, str(SUPERVISOR_ROOT))

    _module(
        "models",
        AgentHealthRecord=object,
        AgentHealthStatus=lambda value: value,
    )
    _load_module("db.connection", SUPERVISOR_ROOT / "db" / "connection.py")

    module = _load_module(
        "health_store_under_test",
        SUPERVISOR_ROOT / "db" / "health_store.py",
    )

    store = module.HealthStore()

    assert store.conn is None
