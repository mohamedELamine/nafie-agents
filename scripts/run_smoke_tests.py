#!/usr/bin/env python3
"""Run curated self-contained smoke tests without pytest."""

from __future__ import annotations

import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]

TEST_FILES = [
    ROOT / "agents/analytics/analytics-agent/tests/test_signal_delivery.py",
    ROOT / "agents/analytics/analytics-agent/tests/test_batch_connection_usage.py",
    ROOT / "agents/content/content-agent/tests/test_content_dispatcher.py",
    ROOT / "agents/platform/platform-agent/tests/test_registry_proxy.py",
    ROOT / "agents/support/support-agent/tests/test_ticket_updater.py",
    ROOT / "agents/support/support-agent/tests/test_qdrant_embeddings.py",
    ROOT / "agents/visual_production/visual-production-agent/tests/test_manifest_builder.py",
    ROOT / "agents/visual_production/visual-production-agent/tests/test_review_decision.py",
    ROOT / "supervisor/supervisor-agent/tests/test_listener_runtime.py",
    ROOT / "supervisor/supervisor-agent/tests/test_db_lazy_store.py",
]


RUNNER = """
import importlib.util
import pathlib
import sys

root = pathlib.Path(sys.argv[1])
path = pathlib.Path(sys.argv[2])
sys.path.insert(0, str(root))

module_name = f"smoke_{path.stem}"
spec = importlib.util.spec_from_file_location(module_name, path)
module = importlib.util.module_from_spec(spec)
sys.modules[module_name] = module
assert spec.loader is not None
spec.loader.exec_module(module)

count = 0
for name in sorted(dir(module)):
    if name.startswith("test_") and callable(getattr(module, name)):
        getattr(module, name)()
        count += 1

print(f"COUNT={count}")
"""


def main() -> int:
    failures: list[tuple[pathlib.Path, str]] = []

    for path in TEST_FILES:
        result = subprocess.run(
            [sys.executable, "-c", RUNNER, str(ROOT), str(path)],
            cwd=ROOT,
            text=True,
            capture_output=True,
        )
        if result.returncode == 0:
            count_line = next(
                (line for line in result.stdout.splitlines() if line.startswith("COUNT=")),
                "COUNT=0",
            )
            count = int(count_line.split("=", 1)[1])
            print(f"PASS {path.relative_to(ROOT)} ({count} tests)")
        else:
            failures.append((path, (result.stdout + "\n" + result.stderr).strip()))
            print(f"FAIL {path.relative_to(ROOT)}")

    if failures:
        print("\nFailures:")
        for path, tb in failures:
            print(f"\n## {path.relative_to(ROOT)}")
            print(tb)
        return 1

    print(f"\nAll smoke tests passed ({len(TEST_FILES)} files).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
