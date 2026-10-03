"""Small immutable experiment definitions; no changes to the reference schema."""

from dataclasses import asdict, dataclass
from math import isfinite

import numpy as np

from concord.contracts import require_id
from concord.features.reference import FEATURE_NAMES, FEATURE_SCHEMA_SHA256
from concord.metadata import content_sha256

# Group definitions refer to ordered C3 columns, including their relevant cosines.
GROUPS = (
    ("name", tuple(range(10)) + (24, 25, 29, 30)),
    ("address", tuple(range(10, 18)) + (26, 27, 31)),
    ("numeric", tuple(range(18, 24))),
    ("retrieval", (32,) + tuple(range(33, 38))),
    ("competition", tuple(range(38, 55))),
    ("cross_script", tuple(range(55, 59))),
)


@dataclass(frozen=True, slots=True)
class ExperimentDefinition:
    name: str
    scorer: str = "lightgbm"
    removed_group: str | None = None
    retrieval: str = "reference"
    seed: int = 42
    schema_version: str = "concord.c4.experiment-definition.v1"

    def __post_init__(self):
        require_id(self.name)
        if self.scorer not in ("lightgbm", "logistic"):
            raise ValueError("unsupported bounded challenger")
        if self.removed_group is not None and self.removed_group not in dict(GROUPS):
            raise ValueError("unknown feature group")
        if self.retrieval not in ("reference", "k1", "no_reverse", "transliterated_name"):
            raise ValueError("unknown bounded retrieval variant")
        if type(self.seed) is not int or self.seed < 0 or self.scorer == "lightgbm" and self.seed != 42:
            raise ValueError("reference seed is frozen; challenger seeds must be explicit")
        if self.schema_version != "concord.c4.experiment-definition.v1":
            raise ValueError("unsupported experiment definition")

    @property
    def mask(self):
        return tuple(i for name, indices in GROUPS if name == self.removed_group for i in indices)

    @property
    def sha256(self):
        return content_sha256({**asdict(self), "feature_schema_sha256": FEATURE_SCHEMA_SHA256,
                               "removed_features": [FEATURE_NAMES[i] for i in self.mask],
                               "ablation_policy": "zero-mask at train and score; retrain, no reordering.v1"})

    def matrix(self, matrix):
        result = np.asarray(matrix, dtype=np.float32).copy()
        if result.ndim != 2 or result.shape[1] != 59 or not np.isfinite(result).all():
            raise ValueError("C4 consumes the finite ordered 59-column contract")
        result[:, self.mask] = 0
        return result


@dataclass(frozen=True, slots=True)
class StabilityObservation:
    s1_id: str
    perturbation: str
    reference_targets: tuple[str, ...]
    perturbed_targets: tuple[str, ...]

    def __post_init__(self):
        require_id(self.s1_id)
        require_id(self.perturbation)
        for values in (self.reference_targets, self.perturbed_targets):
            if type(values) is not tuple or values != tuple(sorted(set(values))):
                raise ValueError("immutable sorted decision sets required")
            for value in values:
                require_id(value)


@dataclass(frozen=True, slots=True)
class ScaleObservation:
    query_count: int
    target_count: int
    candidate_count: int
    repetition: int
    stage: str
    wall_seconds: float
    sampled_peak_rss_bytes: int
    start_rss_bytes: int
    samples: int

    def __post_init__(self):
        require_id(self.stage)
        for value in (self.query_count, self.target_count, self.candidate_count,
                      self.repetition, self.sampled_peak_rss_bytes, self.start_rss_bytes, self.samples):
            if type(value) is not int or value < 0:
                raise ValueError("nonnegative scale counts required")
        if not isfinite(self.wall_seconds) or self.wall_seconds <= 0 or self.samples < 2:
            raise ValueError("executed positive duration and RSS samples required")


def experiment_suite():
    return (ExperimentDefinition("reference"), ExperimentDefinition("logistic", scorer="logistic"),
            *(ExperimentDefinition("without_" + name, removed_group=name) for name, _ in GROUPS),
            *(ExperimentDefinition(name, retrieval=name) for name in ("k1", "no_reverse", "transliterated_name")),
            ExperimentDefinition("logistic_seed7", scorer="logistic", seed=7))
