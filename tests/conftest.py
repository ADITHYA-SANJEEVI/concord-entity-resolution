import ast
import runpy
import unicodedata
from pathlib import Path

import numpy as np
import pytest
from sklearn.feature_extraction.text import TfidfVectorizer

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def public_fixture():
    return runpy.run_path(str(ROOT / "examples/synthetic/pass_a_fixture.py"))["fixture"]()


@pytest.fixture
def historical_functions():
    """Execute selected preserved definitions without importing the private pipeline."""
    path = ROOT / "src/concord/legacy_amazon/frozen_full_graph_builder.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    selected = [node for node in tree.body if isinstance(node, ast.FunctionDef)
                and node.name in ("fold", "vec", "retrieve", "commit")]
    namespace = {"unicodedata": unicodedata, "np": np, "TfidfVectorizer": TfidfVectorizer}
    exec(compile(ast.Module(body=selected, type_ignores=[]), str(path), "exec"), namespace)
    return namespace
