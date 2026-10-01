"""Portable entry point for the frozen 59-feature production pipeline.

The retrieval and 55-feature stages call the frozen production modules without
changing their algorithms. This wrapper supplies local paths, a no-op volume
object, the four qualified cross-script features, the frozen 59-feature model,
and the final ownership and threshold policy.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import duckdb
import joblib
import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from .qualified_crossscript_generator import compute_4_features


HERE = Path(__file__).resolve().parent
ARTIFACTS = HERE / "artifacts"
MODEL_PATH = ARTIFACTS / "cross_script_59_reproduced_model.joblib"
SCHEMA_PATH = ARTIFACTS / "ordered_59_feature_schema.json"
THRESHOLD = {"S2": 0.64, "S3": 0.64}
EXPECTED = {
    "model": "c5b0e2246794f5e79d6cfed1e16d82040d682bdee4cf94eccb760d61e69d6610",
    "schema": "ed766a44c8c5bb20abc8d6473ba95cffd9755bd4a65c88752b34adab0705c5f0",
}


class LocalVolume:
    """Compatibility object for the historical checkpointing functions."""

    def reload(self) -> None:
        return None

    def commit(self) -> None:
        return None


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )


def validate_inputs(train_dir: Path, test_dir: Path) -> list[str]:
    required = [
        train_dir / "train_source1.tsv",
        train_dir / "train_source2.tsv",
        train_dir / "train_source3.tsv",
        train_dir / "train_ground_truth.tsv",
        test_dir / "test_source1.tsv",
        test_dir / "test_source2.tsv",
        test_dir / "test_source3.tsv",
    ]
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise FileNotFoundError("Missing organizer files: " + ", ".join(missing))

    expected_columns = ["entity_id", "business_name", "business_address", "country"]
    for path in required:
        with path.open("r", encoding="utf-8", newline="") as handle:
            header = next(csv.reader(handle, delimiter="\t"), [])
        expected = (
            ["source1_entity_id", "matched_entity_ids"]
            if path.name == "train_ground_truth.tsv"
            else expected_columns
        )
        if header != expected:
            raise ValueError(f"Unexpected header in {path}: {header!r}")

    for path, expected_hash in ((MODEL_PATH, EXPECTED["model"]), (SCHEMA_PATH, EXPECTED["schema"])):
        observed = sha256(path)
        if observed != expected_hash:
            raise RuntimeError(f"Frozen artifact hash mismatch for {path}: {observed}")

    countries = sorted(
        pd.read_csv(test_dir / "test_source1.tsv", sep="\t", usecols=["country"], dtype=str)[
            "country"
        ].unique()
    )
    if not countries:
        raise RuntimeError("No countries found in test_source1.tsv")
    return countries


def configure_frozen_modules(data_root: Path, test_dir: Path, work_dir: Path, workers: int):
    from . import frozen_full_graph_builder as retrieval
    from . import frozen_stage1_55_scorer as scorer
    from . import frozen_test_production as production

    production.MOUNT = work_dir
    production.INPUT = data_root
    production.ROOT = work_dir / "test_production_stage1_55"
    production.RETRIEVAL = production.ROOT / "retrieval"
    production.STAGE1 = production.ROOT / "stage1"
    production.OUTPUT = production.ROOT / "output"
    production.FROZEN_STAGE1 = work_dir / "unused_frozen_stage1"
    production.CODE = HERE
    production.TEST = test_dir
    production.WORKERS = workers

    retrieval.MOUNT = work_dir
    retrieval.INPUT = data_root
    retrieval.OUT = production.RETRIEVAL

    scorer.MOUNT = work_dir
    scorer.INPUT = data_root
    scorer.RETRIEVAL = production.RETRIEVAL
    scorer.OUT = production.STAGE1
    scorer.CODE = HERE
    scorer.WORKERS = workers
    return production


def run_retrieval_and_base_features(
    production, countries: list[str], workers: int
) -> dict[str, object]:
    volume = LocalVolume()
    result: dict[str, object] = {"retrieval": {}, "base_features": {}}
    for country in countries:
        result["retrieval"][country] = production.retrieve_country(country, volume)
    for country in countries:
        result["base_features"][country] = production.feature_country(country, volume)
    return result


def load_raw_lookup(test_dir: Path, source: int, country: str, key: str) -> dict[str, dict[str, str]]:
    result: dict[str, dict[str, str]] = {}
    path = test_dir / f"test_source{source}.tsv"
    for frame in pd.read_csv(
        path,
        sep="\t",
        usecols=["entity_id", "business_name", "business_address", "country"],
        chunksize=250_000,
        dtype=str,
        keep_default_na=False,
    ):
        selected = frame[frame["country"].eq(country)]
        for row in selected.itertuples(index=False):
            result[getattr(row, "entity_id")] = {
                "business_name": getattr(row, "business_name"),
                "business_address": getattr(row, "business_address"),
            }
    return result


def score_country(
    country: str,
    test_dir: Path,
    work_dir: Path,
    model,
    features: list[str],
) -> dict[str, object]:
    started = time.time()
    full_path = work_dir / "test_production_stage1_55" / "stage1" / "full_features" / f"{country}.parquet"
    if not full_path.is_file():
        raise FileNotFoundError(full_path)

    score_dir = work_dir / "crossscript_59" / "scores" / country
    score_dir.mkdir(parents=True, exist_ok=True)
    q_map = load_raw_lookup(test_dir, 1, country, "s1_id")
    t_map = load_raw_lookup(test_dir, 2, country, "target_id")
    t_map.update(load_raw_lookup(test_dir, 3, country, "target_id"))

    parquet = pq.ParquetFile(full_path)
    rows = 0
    for row_group in range(parquet.num_row_groups):
        destination = score_dir / f"part_{row_group:05d}.parquet"
        if destination.exists():
            rows += pq.ParquetFile(destination).metadata.num_rows
            continue
        frame = parquet.read_row_group(
            row_group,
            columns=["s1_id", "target_id", "country", "source"] + features[:55],
        ).to_pandas()
        f55, f56, f57, f58 = compute_4_features(frame, q_map, t_map)
        frame["f55"] = f55
        frame["f56"] = f56
        frame["f57"] = f57
        frame["f58"] = f58
        matrix = frame[features].to_numpy(dtype=np.float32)
        scores = model.predict_proba(matrix)[:, 1]
        if not np.isfinite(scores).all():
            raise RuntimeError(f"Non-finite scores in {country} row group {row_group}")
        output = pa.Table.from_pydict(
            {
                "s1_id": frame["s1_id"],
                "target_id": frame["target_id"],
                "country": frame["country"],
                "source": frame["source"],
                "score": scores,
            }
        )
        temporary = destination.with_suffix(".tmp.parquet")
        pq.write_table(output, temporary, compression="zstd", row_group_size=250_000)
        os.replace(temporary, destination)
        rows += len(frame)

    del q_map, t_map
    return {
        "country": country,
        "rows": rows,
        "parts": parquet.num_row_groups,
        "seconds": time.time() - started,
    }


def run_scoring(countries: list[str], test_dir: Path, work_dir: Path) -> dict[str, object]:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    features = schema["ordered_features"]
    if len(features) != 59 or features[-4:] != ["f55", "f56", "f57", "f58"]:
        raise RuntimeError("Frozen 59-feature schema is invalid")
    model = joblib.load(MODEL_PATH)
    if model.booster_.num_feature() != 59 or model.booster_.num_trees() != 600:
        raise RuntimeError("Frozen model structure does not match the production contract")
    return {
        country: score_country(country, test_dir, work_dir, model, features)
        for country in countries
    }


def finalize(test_dir: Path, work_dir: Path, output_dir: Path, threads: int) -> dict[str, object]:
    output_dir.mkdir(parents=True, exist_ok=True)
    matching_path = output_dir / "matching_results.tsv"
    candidate_path = output_dir / "candidate_pairs.tsv"
    score_glob = str(work_dir / "crossscript_59" / "scores" / "*" / "*.parquet").replace("\\", "/")
    graph_glob = str(
        work_dir / "test_production_stage1_55" / "retrieval" / "candidate_graph" / "*.parquet"
    ).replace("\\", "/")
    source1 = str(test_dir / "test_source1.tsv").replace("\\", "/")
    winners = work_dir / "crossscript_59" / "target_winners.parquet"
    winners.parent.mkdir(parents=True, exist_ok=True)
    winners_sql = str(winners).replace("\\", "/")
    matching_sql = str(matching_path).replace("\\", "/")
    candidate_sql = str(candidate_path).replace("\\", "/")

    con = duckdb.connect()
    con.execute(f"PRAGMA threads={threads}")
    con.execute("PRAGMA memory_limit='96GB'")
    temp_dir = str(work_dir / "duckdb_tmp").replace("\\", "/")
    (work_dir / "duckdb_tmp").mkdir(parents=True, exist_ok=True)
    con.execute(f"PRAGMA temp_directory='{temp_dir}'")
    con.execute(
        f"""
        COPY (
          SELECT s1_id,target_id,country,source,score
          FROM (
            SELECT *,row_number() OVER(
              PARTITION BY target_id ORDER BY score DESC,s1_id ASC
            ) AS owner_rank
            FROM read_parquet('{score_glob}')
          )
          WHERE owner_rank=1
          ORDER BY target_id
        ) TO '{winners_sql}' (FORMAT PARQUET,COMPRESSION ZSTD,ROW_GROUP_SIZE 250000)
        """
    )
    con.execute(
        f"""
        COPY (
          WITH q AS (
            SELECT entity_id AS source1_entity_id
            FROM read_csv('{source1}',delim='\t',header=true,all_varchar=true)
          ), p AS (
            SELECT s1_id,string_agg(target_id,',' ORDER BY score DESC,target_id ASC) AS matched_entity_ids
            FROM read_parquet('{winners_sql}')
            WHERE (source='S2' AND score>={THRESHOLD['S2']})
               OR (source='S3' AND score>={THRESHOLD['S3']})
            GROUP BY s1_id
          )
          SELECT q.source1_entity_id,p.matched_entity_ids
          FROM q LEFT JOIN p ON q.source1_entity_id=p.s1_id
          ORDER BY q.source1_entity_id
        ) TO '{matching_sql}' (HEADER,DELIMITER '\t',NULL '')
        """
    )
    con.execute(
        f"""
        COPY (
          WITH q AS (
            SELECT entity_id AS source1_entity_id
            FROM read_csv('{source1}',delim='\t',header=true,all_varchar=true)
          ), c AS (
            SELECT s1_id,string_agg(target_id,',' ORDER BY target_id ASC) AS candidate_entity_ids
            FROM read_parquet('{graph_glob}') GROUP BY s1_id
          )
          SELECT q.source1_entity_id,coalesce(c.candidate_entity_ids,'') AS candidate_entity_ids
          FROM q LEFT JOIN c ON q.source1_entity_id=c.s1_id
          ORDER BY q.source1_entity_id
        ) TO '{candidate_sql}' (HEADER,DELIMITER '\t',NULL '')
        """
    )
    selected_links = con.execute(
        f"SELECT count(*) FROM read_parquet('{winners_sql}') WHERE score>=0.64"
    ).fetchone()[0]
    con.close()
    return {
        "matching_results": str(matching_path),
        "matching_results_sha256": sha256(matching_path),
        "candidate_pairs": str(candidate_path),
        "candidate_pairs_sha256": sha256(candidate_path),
        "selected_links": int(selected_links),
        "thresholds": THRESHOLD,
        "ownership": "score DESC, s1_id ASC",
    }


def run_validator(test_dir: Path, output_dir: Path) -> dict[str, object]:
    command = [
        sys.executable,
        str(HERE / "validate_submission.py"),
        "--matching",
        str(output_dir / "matching_results.tsv"),
        "--candidate",
        str(output_dir / "candidate_pairs.tsv"),
        "--test-dir",
        str(test_dir),
        "--check-ids",
    ]
    completed = subprocess.run(command, text=True, capture_output=True, check=False)
    return {
        "command": command,
        "returncode": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Reproduce the frozen business entity resolution output")
    parser.add_argument("--train", type=Path, required=True, help="Organizer dataset/train directory")
    parser.add_argument("--test", type=Path, required=True, help="Organizer dataset/test directory")
    parser.add_argument("--output", type=Path, required=True, help="Directory for final TSV files")
    parser.add_argument("--work-dir", type=Path, required=True, help="Checkpoint and intermediate directory")
    parser.add_argument("--workers", type=int, default=min(32, os.cpu_count() or 1))
    parser.add_argument(
        "--stage",
        choices=["all", "retrieve", "features", "score", "finalize", "validate"],
        default="all",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    train_dir = args.train.resolve()
    test_dir = args.test.resolve()
    output_dir = args.output.resolve()
    work_dir = args.work_dir.resolve()
    data_root = train_dir.parent
    work_dir.mkdir(parents=True, exist_ok=True)
    countries = validate_inputs(train_dir, test_dir)
    production = configure_frozen_modules(data_root, test_dir, work_dir, args.workers)
    report: dict[str, object] = {
        "countries": countries,
        "model_sha256": sha256(MODEL_PATH),
        "schema_sha256": sha256(SCHEMA_PATH),
        "stage": args.stage,
    }

    if args.stage in ("all", "retrieve"):
        volume = LocalVolume()
        report["retrieval"] = {
            country: production.retrieve_country(country, volume) for country in countries
        }
    if args.stage in ("all", "features"):
        volume = LocalVolume()
        report["base_features"] = {
            country: production.feature_country(country, volume) for country in countries
        }
    if args.stage in ("all", "score"):
        report["scoring"] = run_scoring(countries, test_dir, work_dir)
    if args.stage in ("all", "finalize"):
        report["finalization"] = finalize(test_dir, work_dir, output_dir, args.workers)
    if args.stage in ("all", "validate"):
        report["validation"] = run_validator(test_dir, output_dir)
        if report["validation"]["returncode"] != 0:
            write_json(work_dir / "run_report.json", report)
            print(report["validation"]["stdout"], end="")
            print(report["validation"]["stderr"], end="", file=sys.stderr)
            return 1

    write_json(work_dir / "run_report.json", report)
    print(json.dumps(report, indent=2, sort_keys=True, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
