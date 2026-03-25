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
    """HealthStore يمكن استيراده وإنشاؤه بدون DATABASE_URL —
    الاتصال لا يحدث عند الاستيراد، بل عند استدعاء get_conn() فقط."""
    os.environ.pop("DATABASE_URL", None)
    sys.path.insert(0, str(SUPERVISOR_ROOT))

    _module(
        "models",
        AgentHealthRecord=object,
        AgentHealthStatus=lambda value: value,
    )
    conn_module = _load_module(
        "db.connection", SUPERVISOR_ROOT / "db" / "connection.py"
    )

    module = _load_module(
        "health_store_under_test",
        SUPERVISOR_ROOT / "db" / "health_store.py",
    )

    # الاستيراد يجب أن ينجح بدون DATABASE_URL
    store = module.HealthStore()
    assert store is not None

    # لا يوجد self.conn بعد التحويل إلى pool pattern
    assert not hasattr(store, "conn")

    # استدعاء get_conn() بدون init_pool يرفع RuntimeError — ليس عند الاستيراد
    import pytest
    with pytest.raises(RuntimeError, match="not initialised"):
        with conn_module.get_conn():
            pass
