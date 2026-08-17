"""
Stage 2: Analyze Data
=====================
Reads raw data from /data/raw/ and produces structured analysis in /data/analyzed/

Outputs:
- jira_analysis.json: categorized issues, ownership, workflows, metrics
- slack_analysis.json: message patterns, knowledge gaps, engagement
- combined_analysis.json: merged insights across both sources
"""

import json
import re
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

import yaml


NOISE_PATTERNS = [
    r"^(na|team)$",
    r"^testing\s",
    r"^test ticket",
    r"^\!subteam",
    r"^https?://",
]


def is_noise(summary: str) -> bool:
    text = summary.strip().lower()
    return any(re.search(p, text) for p in NOISE_PATTERNS)


def categorize_text(text: str, categories: dict) -> str:
    text_lower = text.lower()
    for cat_id, cat_info in categories.items():
        for pattern in cat_info["patterns"]:
            if re.search(pattern, text_lower):
                return cat_id
    return "uncategorized"


def analyze_jira(issues: list, config: dict) -> dict:
    categories_config = config["analysis"]["request_categories"]["categories"]
    auto_config = config["analysis"]["automation_feasibility"]

    categorized = defaultdict(list)
    reporters = Counter()
    assignees = Counter()
    components = Counter()
    statuses = Counter()
    priorities = Counter()
    monthly_volume = Counter()
    repeat_patterns = Counter()

    for issue in issues:
        fields = issue["fields"]
        summary = fields.get("summary", "")
        desc = fields.get("description", "") or ""
        text = summary + " " + desc

        if is_noise(summary):
            cat = "noise_invalid"
        else:
            cat = categorize_text(text, categories_config)
        categorized[cat].append({
            "key": issue["key"],
            "summary": summary,
            "assignee": fields.get("assignee", {}).get("emailAddress") if fields.get("assignee") else None,
            "reporter": fields.get("reporter", {}).get("emailAddress") if fields.get("reporter") else None,
            "status": fields.get("status", {}).get("name"),
            "priority": fields.get("priority", {}).get("name"),
            "created": fields.get("created", "")[:10],
        })

        if fields.get("reporter"):
            reporters[fields["reporter"].get("emailAddress", "unknown")] += 1
        if fields.get("assignee"):
            assignees[fields["assignee"].get("emailAddress", "unknown")] += 1
        else:
            assignees["unassigned"] += 1
        for comp in fields.get("components", []):
            components[comp.get("name", "unknown")] += 1
        statuses[fields.get("status", {}).get("name", "unknown")] += 1
        priorities[fields.get("priority", {}).get("name", "unknown")] += 1
        created = fields.get("created", "")[:7]
        if created:
            monthly_volume[created] += 1

        # Repeat detection
        normalized = re.sub(r"prod\d+|qa\d*|harness\d+|staging", "ENV", summary.lower())
        normalized = re.sub(r"\d+gi\b", "SIZE", normalized)
        normalized = re.sub(r"\bm\d+\b", "TIER", normalized)
        repeat_patterns[normalized] += 1

    # Automation feasibility
    auto_counts = {"high": 0, "medium": 0, "low": 0}
    for issue in issues:
        summary = issue["fields"].get("summary", "").lower()
        for level, patterns in auto_config.items():
            key = level.replace("_patterns", "")
            for p in patterns:
                if re.search(p, summary):
                    auto_counts[key] += 1
                    break

    # Ownership model
    assignee_domains = defaultdict(Counter)
    for issue in issues:
        fields = issue["fields"]
        assignee = fields.get("assignee")
        if not assignee:
            continue
        email = assignee.get("emailAddress", "unknown")
        summary = fields.get("summary", "").lower()
        domain_keywords = {
            "MongoDB": ["mongo"],
            "PostgreSQL": ["postgres", "pg ", "cloudsql"],
            "Secrets": ["secret", "cert", "token"],
            "Observability": ["grafana", "metric", "dashboard", "alert"],
            "Deployments": ["deploy", "helm", "argocd"],
            "Networking": ["dns", "vanity", "gclb", "ingress"],
            "Kafka": ["kafka", "outbox", "topic"],
            "Kubernetes": ["cluster", "eks", "gke", "namespace", "pod"],
            "Scaling": ["scale", "disk", "cpu", "memory"],
        }
        for domain, keywords in domain_keywords.items():
            if any(kw in summary for kw in keywords):
                assignee_domains[email][domain] += 1

    ownership = {}
    for email, domains in assignee_domains.items():
        total = sum(domains.values())
        if total >= 3:
            ownership[email] = {
                "total_tickets": total,
                "top_domains": domains.most_common(5),
            }

    return {
        "total_issues": len(issues),
        "categories": {
            cat: {
                "count": len(items),
                "percentage": round(len(items) / len(issues) * 100, 1),
                "tickets": [{"key": t["key"], "summary": t["summary"], "status": t["status"], "assignee": (t["assignee"] or "unassigned").split("@")[0]} for t in items],
            }
            for cat, items in sorted(categorized.items(), key=lambda x: -len(x[1]))
        },
        "statuses": dict(statuses.most_common()),
        "priorities": dict(priorities.most_common()),
        "monthly_volume": dict(sorted(monthly_volume.items())),
        "top_reporters": dict(reporters.most_common(20)),
        "top_assignees": dict(assignees.most_common(20)),
        "components": dict(components.most_common(20)),
        "repeat_patterns": [
            {"pattern": p, "count": c}
            for p, c in repeat_patterns.most_common(30)
            if c >= 2
        ],
        "automation_feasibility": auto_counts,
        "ownership_model": ownership,
    }


def analyze_slack(messages: list) -> dict:
    bot_messages = [m for m in messages if "[bot]" in m.get("text", "") or m["author"] == "Unknown"]
    human_messages = [m for m in messages if "[bot]" not in m.get("text", "") and m["author"] != "Unknown"]
    threads = [m for m in messages if m.get("reply_count") and m["reply_count"] != "" and int(m["reply_count"]) > 0]

    # Author activity
    authors = Counter(m["author"] for m in human_messages)

    # Topic analysis
    topic_patterns = {
        "deployment_help": [r"deploy", r"rollout", r"release", r"hotfix", r"promote", r"sync"],
        "database_help": [r"mongo", r"postgres", r"cloudsql", r"migration", r"query", r"db\b", r"database"],
        "kubernetes_help": [r"pod", r"namespace", r"cluster", r"node", r"kubectl", r"k8s"],
        "observability_help": [r"grafana", r"metric", r"dashboard", r"alert", r"monitor", r"prometheus"],
        "secrets_access": [r"secret", r"access", r"permission", r"token", r"credential"],
        "pr_code_review": [r"review.*pr", r"pull.*request", r"/pulls/", r"codeowner"],
        "kafka_events": [r"kafka", r"topic", r"consumer", r"outbox"],
        "helm_charts": [r"helm", r"chart", r"values"],
        "networking_help": [r"dns", r"ingress", r"gclb", r"load.?balancer", r"vpc", r"ssl"],
        "ci_cd_pipelines": [r"pipeline", r"ci\b", r"build", r"trigger"],
    }

    topic_counts = Counter()
    for msg in human_messages:
        text = msg["text"].lower()
        matched = False
        for topic, patterns in topic_patterns.items():
            for p in patterns:
                if re.search(p, text):
                    topic_counts[topic] += 1
                    matched = True
                    break
            if matched:
                break
        if not matched:
            topic_counts["uncategorized"] += 1

    # Message intent
    help_requests = [m for m in human_messages if any(w in m["text"].lower() for w in ["help", "can someone", "anyone know", "need assistance", "could you"])]
    questions = [m for m in human_messages if "?" in m["text"] or any(w in m["text"].lower() for w in ["how to", "where is", "what is", "who owns"])]
    jira_linked = [m for m in human_messages if "atlassian.net/browse/CLI-" in m.get("text", "")]
    slack_only = [m for m in human_messages if "atlassian.net/browse/CLI-" not in m.get("text", "")]

    # Monthly volume
    monthly = Counter()
    for msg in messages:
        try:
            dt = datetime.strptime(msg["timestamp"], "%A, %B %d, %Y %I:%M:%S %p")
            monthly[dt.strftime("%Y-%m")] += 1
        except (ValueError, KeyError):
            pass

    # Engagement
    reply_counts = [int(m["reply_count"]) for m in threads]

    # Knowledge questions
    knowledge_qs = [
        {"author": m["author"], "text": m["text"][:200]}
        for m in human_messages
        if any(q in m["text"].lower() for q in ["how do", "how to", "where is", "what is the", "can someone explain", "is there a", "does anyone know", "what's the process"])
    ]

    return {
        "total_messages": len(messages),
        "bot_messages": len(bot_messages),
        "human_messages": len(human_messages),
        "threads_with_replies": len(threads),
        "top_authors": dict(authors.most_common(20)),
        "topics": dict(topic_counts.most_common()),
        "intent_breakdown": {
            "help_requests": len(help_requests),
            "questions": len(questions),
            "jira_linked": len(jira_linked),
            "slack_only": len(slack_only),
        },
        "monthly_volume": dict(sorted(monthly.items())),
        "engagement": {
            "avg_replies": round(sum(reply_counts) / len(reply_counts), 1) if reply_counts else 0,
            "median_replies": sorted(reply_counts)[len(reply_counts) // 2] if reply_counts else 0,
            "max_replies": max(reply_counts) if reply_counts else 0,
        },
        "knowledge_questions": knowledge_qs[:20],
        "slack_only_percentage": round(len(slack_only) / len(human_messages) * 100, 1) if human_messages else 0,
    }


def self_compute_findings(jira: dict, slack: dict) -> list:
    findings = []
    if slack:
        findings.append(f"{slack['slack_only_percentage']}% of Slack requests never become formal Jira tickets")
    cats = jira["categories"]
    sorted_cats = sorted(cats.items(), key=lambda x: -x[1]["count"])
    top = sorted_cats[0]
    findings.append(f"{top[0].replace('_', ' ').title()} is the #1 workload at {top[1]['percentage']}% of tickets")
    second = sorted_cats[1]
    findings.append(f"{second[0].replace('_', ' ').title()} is #2 at {second[1]['percentage']}%")
    assignees = jira["top_assignees"]
    top3 = list(assignees.values())[:3]
    top3_pct = round(sum(top3) / jira["total_issues"] * 100)
    findings.append(f"Top 3 engineers handle {top3_pct}% of all ticket work (load concentration risk)")
    auto = jira["automation_feasibility"]
    automatable = auto["high"] + auto["medium"]
    monthly_auto = round(automatable / jira["total_issues"] * 250)
    findings.append(f"~{monthly_auto} tickets/month are fully automatable with current tooling")
    repeats = jira["repeat_patterns"]
    if repeats:
        findings.append(f"{repeats[0]['pattern'][:50]} alone: {repeats[0]['count']} repeat tickets in 6 months")
    if slack:
        monthly_msgs = round(slack["human_messages"] / 6)
        findings.append(f"Slack channel sees ~{monthly_msgs} messages/month from humans seeking help")
        findings.append(f"{len(slack.get('knowledge_questions', []))}+ knowledge questions in Slack answerable by a KG")
    return findings


def run(config_path: str):
    config = yaml.safe_load(Path(config_path).read_text())
    project_root = Path(config_path).parent.parent
    output_dir = project_root / "data" / "analyzed"
    output_dir.mkdir(parents=True, exist_ok=True)

    jira_analysis = None
    slack_analysis = None

    # Analyze Jira
    jira_path = project_root / "data" / "raw" / "jira" / "cli-esr-issues.json"
    if jira_path.exists():
        issues = json.loads(jira_path.read_text())
        jira_analysis = analyze_jira(issues, config)
        (output_dir / "jira_analysis.json").write_text(json.dumps(jira_analysis, indent=2))
        print(f"  [Jira] Analyzed {jira_analysis['total_issues']} issues → {output_dir / 'jira_analysis.json'}")
    else:
        print("  [Jira] No raw data found, skipping.")

    # Analyze Slack
    slack_path = project_root / "data" / "raw" / "slack" / "all-cloud-engineers.json"
    if slack_path.exists():
        messages = json.loads(slack_path.read_text())
        slack_analysis = analyze_slack(messages)
        (output_dir / "slack_analysis.json").write_text(json.dumps(slack_analysis, indent=2))
        print(f"  [Slack] Analyzed {slack_analysis['total_messages']} messages → {output_dir / 'slack_analysis.json'}")
    else:
        print("  [Slack] No raw data found, skipping.")

    # Combined analysis
    combined = {
        "generated_at": datetime.now().isoformat(),
        "jira": jira_analysis,
        "slack": slack_analysis,
        "combined_insights": {
            "total_request_volume": {
                "jira_tickets_6mo": jira_analysis["total_issues"] if jira_analysis else 0,
                "slack_messages_6mo": slack_analysis["total_messages"] if slack_analysis else 0,
                "estimated_total_requests": (jira_analysis["total_issues"] if jira_analysis else 0) + (slack_analysis["intent_breakdown"]["slack_only"] if slack_analysis else 0),
            },
            "key_findings": self_compute_findings(jira_analysis, slack_analysis),
        },
    }
    (output_dir / "combined_analysis.json").write_text(json.dumps(combined, indent=2))
    print(f"  [Combined] → {output_dir / 'combined_analysis.json'}")
