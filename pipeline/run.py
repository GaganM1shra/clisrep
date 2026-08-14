#!/usr/bin/env python3
"""
CLISREP Analysis Pipeline
==========================
Orchestrates: S1 (Gather) → S2 (Analyze) → S3 (Generate KG + Dashboard)

Usage:
    python pipeline/run.py                  # Run all stages
    python pipeline/run.py --stage gather   # Run only Stage 1
    python pipeline/run.py --stage analyze  # Run only Stage 2
    python pipeline/run.py --stage generate # Run only Stage 3
"""

import argparse
import sys
from pathlib import Path

PIPELINE_DIR = Path(__file__).parent
PROJECT_ROOT = PIPELINE_DIR.parent

sys.path.insert(0, str(PIPELINE_DIR))

from stages.s1_gather import run as gather
from stages.s2_analyze import run as analyze
from stages.s3_generate import run as generate


def main():
    parser = argparse.ArgumentParser(description="CLISREP Analysis Pipeline")
    parser.add_argument("--stage", choices=["gather", "analyze", "generate", "all"], default="all")
    parser.add_argument("--config", default=str(PIPELINE_DIR / "config.yaml"))
    args = parser.parse_args()

    print("=" * 60)
    print("  CLISREP Analysis Pipeline v1.0.0")
    print("=" * 60)
    print()

    if args.stage in ("all", "gather"):
        print("[S1] Gathering data...")
        gather(args.config)
        print("[S1] Done.\n")

    if args.stage in ("all", "analyze"):
        print("[S2] Analyzing data...")
        analyze(args.config)
        print("[S2] Done.\n")

    if args.stage in ("all", "generate"):
        print("[S3] Generating KG + Dashboard...")
        generate(args.config)
        print("[S3] Done.\n")

    print("=" * 60)
    print("  Pipeline complete!")
    print(f"  Dashboard: {PROJECT_ROOT / 'dashboard.html'}")
    print(f"  Knowledge Graph: {PROJECT_ROOT / 'knowledge-graph/'}")
    print("=" * 60)


if __name__ == "__main__":
    main()
