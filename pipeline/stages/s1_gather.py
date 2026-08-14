"""
Stage 1: Gather Data
====================
Collects raw data from configured sources into /data/raw/

Currently supports:
- Jira (via exported JSON or live API)
- Slack (via bot dump JSON)

For live API gathering, this stage requires MCP or API credentials.
For now, it validates that raw data files exist and are parseable.
"""

import json
from pathlib import Path

import yaml


def run(config_path: str):
    config = yaml.safe_load(Path(config_path).read_text())
    project_root = Path(config_path).parent.parent
    sources = config["data_sources"]

    results = {"jira": None, "slack": None}

    # Jira
    if sources["jira"]["enabled"]:
        jira_path = project_root / sources["jira"]["raw_output"].lstrip("../")
        if jira_path.exists():
            issues = json.loads(jira_path.read_text())
            print(f"  [Jira] Found {len(issues)} issues in {jira_path.name}")
            results["jira"] = {"path": str(jira_path), "count": len(issues)}
        else:
            print(f"  [Jira] WARNING: No data file at {jira_path}")
            print(f"         Run with MCP/API to fetch, or place exported JSON here.")

    # Slack
    if sources["slack"]["enabled"]:
        slack_path = project_root / sources["slack"]["raw_output"].lstrip("../")
        if slack_path.exists():
            messages = json.loads(slack_path.read_text())
            print(f"  [Slack] Found {len(messages)} messages in {slack_path.name}")
            results["slack"] = {"path": str(slack_path), "count": len(messages)}
        else:
            print(f"  [Slack] WARNING: No data file at {slack_path}")
            print(f"         Get dump from Slack bot and place here.")

    # Write gather manifest
    manifest_path = project_root / "data" / "raw" / "manifest.json"
    manifest_path.write_text(json.dumps(results, indent=2))
    print(f"  [Manifest] Written to {manifest_path}")
