import importlib.util
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


def _install_psycopg2_stubs():
    psycopg2 = types.ModuleType("psycopg2")
    psycopg2.extras = types.ModuleType("psycopg2.extras")
    psycopg2.extras.RealDictCursor = object
    psycopg2.extensions = types.SimpleNamespace(connection=object)
    psycopg2.Error = Exception
    sys.modules["psycopg2"] = psycopg2
    sys.modules["psycopg2.extras"] = psycopg2.extras


def test_registry_db_proxy_releases_connection_after_check_completed():
    _install_psycopg2_stubs()
    registry_module = _load_module(
        "platform_registry_under_test",
        AGENT_ROOT / "db" / "registry.py",
    )
    idempotency_module = _load_module(
        "platform_idempotency_under_test",
        AGENT_ROOT / "db" / "idempotency.py",
    )

    leased_connections = []

    class FakeCursor:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def execute(self, *args, **kwargs):
            return None

        def fetchone(self):
            return None

    class FakeConnection:
        def __init__(self):
            self.rollbacks = 0
            self.released = False

        def cursor(self, *args, **kwargs):
            return FakeCursor()

        def commit(self):
            return None

        def rollback(self):
            self.rollbacks += 1

    @contextmanager
    def get_conn():
        conn = FakeConnection()
        leased_connections.append(conn)
        try:
            yield conn
        finally:
            conn.released = True

    registry = registry_module.ProductRegistry(get_conn)

    completed = idempotency_module.check_completed(
        registry.db,
        "launch:theme-one:1.0",
        "LAUNCH_ENTRY",
    )

    assert completed is False
    assert len(leased_connections) == 1
    assert leased_connections[0].rollbacks == 1
    assert leased_connections[0].released is True
