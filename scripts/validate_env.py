#!/usr/bin/env python3
"""Validate required environment variables against .env.example."""

from __future__ import annotations

import argparse
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List


SCOPE_RE = re.compile(r"\[scopes:\s*([^\]]+)\]", re.IGNORECASE)
ENV_RE = re.compile(r"^([A-Z0-9_]+)=(.*)$")


@dataclass(frozen=True)
class ContractKey:
    key: str
    scopes: tuple[str, ...]


def parse_contract(contract_path: Path) -> List[ContractKey]:
    keys: List[ContractKey] = []
    pending_scopes: tuple[str, ...] = ("all",)

    for raw_line in contract_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line:
            continue

        if line.startswith("#"):
            scope_match = SCOPE_RE.search(line)
            if scope_match:
                scopes = tuple(
                    scope.strip().lower()
                    for scope in scope_match.group(1).split(",")
                    if scope.strip()
                )
                pending_scopes = scopes or ("all",)
            continue

        match = ENV_RE.match(line)
        if not match:
            continue

        keys.append(ContractKey(key=match.group(1), scopes=pending_scopes))
        pending_scopes = ("all",)

    return keys


def filter_keys(keys: Iterable[ContractKey], scope: str | None) -> List[ContractKey]:
    if not scope:
        return list(keys)

    requested = scope.lower()
    return [
        item
        for item in keys
        if "all" in item.scopes or requested in item.scopes
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--env-file",
        default=".env.example",
        help="Path to the environment contract file.",
    )
    parser.add_argument(
        "--scope",
        default=None,
        help="Validate only keys tagged for a specific service scope.",
    )
    args = parser.parse_args()

    contract_path = Path(args.env_file).resolve()
    if not contract_path.exists():
        print(f"❌ Contract file not found: {contract_path}")
        return 1

    keys = filter_keys(parse_contract(contract_path), args.scope)
    if not keys:
        scope_label = args.scope or "all"
        print(f"❌ No keys matched scope: {scope_label}")
        return 1

    missing = False
    for item in keys:
        value = os.environ.get(item.key)
        if value:
            print(f"✅ {item.key}")
        else:
            missing = True
            print(f"❌ {item.key}")

    print(
        f"\nValidated {len(keys)} key(s)"
        + (f" for scope '{args.scope}'." if args.scope else ".")
    )
    return 1 if missing else 0


if __name__ == "__main__":
    raise SystemExit(main())
