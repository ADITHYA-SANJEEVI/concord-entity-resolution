"""Compare regenerated TSV files with the frozen historical outputs."""

from __future__ import annotations

import argparse
import hashlib
from itertools import zip_longest
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def row_count(path: Path) -> int:
    with path.open("rb") as handle:
        return sum(block.count(b"\n") for block in iter(lambda: handle.read(8 * 1024 * 1024), b"")) - 1


def parse(line: str) -> tuple[str, frozenset[str]]:
    source_id, tab, values = line.rstrip("\r\n").partition("\t")
    if not tab:
        raise ValueError(f"Malformed TSV row: {line[:120]!r}")
    return source_id, frozenset(values.split(",")) if values else frozenset()


def semantic_equal(left: Path, right: Path) -> tuple[bool, str | None]:
    with left.open("r", encoding="utf-8", newline="") as a, right.open(
        "r", encoding="utf-8", newline=""
    ) as b:
        if a.readline().rstrip("\r\n") != b.readline().rstrip("\r\n"):
            return False, "header mismatch"
        for line_number, (left_line, right_line) in enumerate(
            zip_longest(a, b), start=2
        ):
            if left_line is None or right_line is None:
                return False, f"row-count mismatch at line {line_number}"
            if parse(left_line) != parse(right_line):
                return False, f"semantic mismatch at line {line_number}"
    return True, None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--frozen", type=Path, required=True)
    parser.add_argument("--regenerated", type=Path, required=True)
    args = parser.parse_args()
    frozen_hash = sha256(args.frozen)
    regenerated_hash = sha256(args.regenerated)
    equivalent, reason = semantic_equal(args.frozen, args.regenerated)
    print(f"frozen_sha256={frozen_hash}")
    print(f"regenerated_sha256={regenerated_hash}")
    print(f"frozen_rows={row_count(args.frozen)}")
    print(f"regenerated_rows={row_count(args.regenerated)}")
    print(f"byte_identical={frozen_hash == regenerated_hash}")
    print(f"semantic_equal={equivalent}")
    if reason:
        print(f"reason={reason}")
    return 0 if equivalent else 1


if __name__ == "__main__":
    raise SystemExit(main())

