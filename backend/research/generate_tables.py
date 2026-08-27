"""
research/generate_tables.py — Aggregate research benchmark results into publication-ready tables.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

RESULTS_DIR = Path("tests/results")
OUTPUT_DIR = Path("research/tables")


def generate_summary_tables():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    records = []
    if not RESULTS_DIR.exists():
        logger.warning("Results dir %s does not exist", RESULTS_DIR)
        return

    for exp_dir in RESULTS_DIR.iterdir():
        if exp_dir.is_dir():
            json_files = list(exp_dir.glob("*.json"))
            for jf in json_files:
                try:
                    with open(jf, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    
                    exp_name = data.get("experiment_name", exp_dir.name)
                    status = data.get("status", "UNKNOWN")
                    ts = data.get("started_at", "")
                    
                    for m in data.get("metrics", []):
                        records.append({
                            "experiment": exp_name,
                            "status": status,
                            "metric": m.get("name"),
                            "value": m.get("value"),
                            "unit": m.get("unit"),
                            "category": m.get("category"),
                            "model": m.get("model_name"),
                            "timestamp": ts,
                        })
                except Exception as exc:
                    logger.warning("Error reading %s: %s", jf, exc)

    if records:
        df = pd.DataFrame(records)
        out_fp = OUTPUT_DIR / "overall_experiment_summary.csv"
        df.to_csv(out_fp, index=False)
        logger.info("Summary table generated: %s (%d metric records)", out_fp, len(df))
    else:
        logger.info("No experiment records found yet.")


if __name__ == "__main__":
    generate_summary_tables()
