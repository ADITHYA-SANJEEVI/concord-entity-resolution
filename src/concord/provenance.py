"""Stable identities for the preserved Amazon ML Challenge 2026 baseline."""

from __future__ import annotations

import hashlib
from pathlib import Path

AMAZON_SUBMISSION_SHA256 = "d0574aab454f2e4798986ed5b488411bd04937b27ac6a9c17601235d4f07618e"
MATCHING_RESULTS_SHA256 = "0153c2ad53f0cfbecce5339075968588d131d3144f6c85c49bb2a5a05741d145"
CANDIDATE_PAIRS_SHA256 = "709164321b318e89763b37277dbcb2e96e40ccdcec93091bfe96c01a6e30a526"


def sha256_file(path: str | Path, chunk_size: int = 1024 * 1024) -> str:
    """Return the lowercase SHA-256 digest of a file without loading it into memory."""

    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()
