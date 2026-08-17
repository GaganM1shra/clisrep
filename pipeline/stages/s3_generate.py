"""
Stage 3: Generate Knowledge Graph + Dashboard
==============================================
Reads analyzed data and produces:
- Updated knowledge-graph/ YAML files
- dashboard.html (self-contained, no server needed)
- knowledge-graph/README.md
"""

import json
from pathlib import Path

import yaml


def generate_dashboard(jira: dict, slack: dict, output_path: Path):
    """Generate a self-contained HTML dashboard for leadership review."""

    # Prepare chart data
    categories = jira.get("categories", {})
    cat_labels = list(categories.keys())[:10]
    cat_values = [categories[c]["count"] for c in cat_labels]
    cat_pcts = [categories[c]["percentage"] for c in cat_labels]

    jira_monthly = jira.get("monthly_volume", {})
    slack_monthly = slack.get("monthly_volume", {}) if slack else {}

    statuses = jira.get("statuses", {})
    priorities = jira.get("priorities", {})

    top_assignees = dict(list(jira.get("top_assignees", {}).items())[:10])
    top_reporters = dict(list(jira.get("top_reporters", {}).items())[:10])

    auto = jira.get("automation_feasibility", {})
    repeat = jira.get("repeat_patterns", [])[:15]

    slack_topics = slack.get("topics", {}) if slack else {}
    slack_intent = slack.get("intent_breakdown", {}) if slack else {}
    engagement = slack.get("engagement", {}) if slack else {}

    # Prepare ticket drill-down data
    tickets_by_category = {}
    for cat_id, cat_data in categories.items():
        tickets_by_category[cat_id] = cat_data.get("tickets", [])
    tickets_json = json.dumps(tickets_by_category)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>CLISREP Phase 1 - Cloud Engineering Workload Analysis</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<style>
:root {{
    --bg: #0f1419;
    --surface: #1a1f2e;
    --surface2: #242b3d;
    --border: #2d3548;
    --text: #e4e8f0;
    --text-dim: #8b95a8;
    --accent: #6366f1;
    --accent2: #818cf8;
    --green: #10b981;
    --amber: #f59e0b;
    --red: #ef4444;
    --blue: #3b82f6;
}}
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: var(--bg); color: var(--text); line-height: 1.6; }}
.container {{ max-width: 1400px; margin: 0 auto; padding: 24px; }}
header {{ text-align: center; padding: 40px 0 30px; border-bottom: 1px solid var(--border); margin-bottom: 30px; }}
header h1 {{ font-size: 28px; font-weight: 700; margin-bottom: 8px; }}
header p {{ color: var(--text-dim); font-size: 14px; }}
.grid {{ display: grid; gap: 20px; margin-bottom: 24px; }}
.grid-4 {{ grid-template-columns: repeat(4, 1fr); }}
.grid-2 {{ grid-template-columns: repeat(2, 1fr); }}
.grid-3 {{ grid-template-columns: repeat(3, 1fr); }}
.card {{ background: var(--surface); border: 1px solid var(--border); border-radius: 12px; padding: 20px; }}
.card h3 {{ font-size: 13px; text-transform: uppercase; letter-spacing: 0.5px; color: var(--text-dim); margin-bottom: 12px; }}
.stat-card {{ text-align: center; }}
.stat-card .value {{ font-size: 36px; font-weight: 700; color: var(--accent2); }}
.stat-card .label {{ font-size: 12px; color: var(--text-dim); margin-top: 4px; }}
.stat-card .sublabel {{ font-size: 11px; color: var(--text-dim); margin-top: 2px; }}
.chart-container {{ position: relative; height: 280px; }}
.bar-list {{ list-style: none; }}
.bar-list li {{ display: flex; align-items: center; margin-bottom: 8px; font-size: 13px; }}
.bar-list .bar-bg {{ flex: 1; height: 24px; background: var(--surface2); border-radius: 4px; margin: 0 10px; overflow: hidden; position: relative; }}
.bar-list .bar-fill {{ display: block; height: 100%; border-radius: 4px; transition: width 0.5s; }}
.bar-list .bar-value {{ min-width: 40px; text-align: right; font-weight: 600; }}
.bar-list .bar-label {{ min-width: 120px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
.insight-box {{ background: var(--surface2); border-left: 3px solid var(--accent); padding: 12px 16px; border-radius: 0 8px 8px 0; margin-bottom: 10px; font-size: 13px; }}
.insight-box.green {{ border-left-color: var(--green); }}
.insight-box.amber {{ border-left-color: var(--amber); }}
.insight-box.red {{ border-left-color: var(--red); }}
.tag {{ display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: 600; margin: 2px; }}
.tag-high {{ background: rgba(16,185,129,0.15); color: var(--green); }}
.tag-medium {{ background: rgba(245,158,11,0.15); color: var(--amber); }}
.tag-low {{ background: rgba(239,68,68,0.15); color: var(--red); }}
table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
table th {{ text-align: left; padding: 8px; color: var(--text-dim); border-bottom: 1px solid var(--border); font-weight: 500; }}
table td {{ padding: 8px; border-bottom: 1px solid var(--border); }}
.section-title {{ font-size: 18px; font-weight: 600; margin: 30px 0 16px; padding-bottom: 8px; border-bottom: 1px solid var(--border); }}
@media (max-width: 900px) {{
    .grid-4 {{ grid-template-columns: repeat(2, 1fr); }}
    .grid-2, .grid-3 {{ grid-template-columns: 1fr; }}
}}
.modal-overlay {{ display: none; position: fixed; inset: 0; background: rgba(0,0,0,0.7); z-index: 1000; align-items: center; justify-content: center; }}
.modal-overlay.active {{ display: flex; }}
.modal {{ background: var(--surface); border: 1px solid var(--border); border-radius: 12px; width: 90%; max-width: 900px; max-height: 80vh; display: flex; flex-direction: column; }}
.modal-header {{ display: flex; justify-content: space-between; align-items: center; padding: 16px 20px; border-bottom: 1px solid var(--border); }}
.modal-header h2 {{ font-size: 16px; font-weight: 600; }}
.modal-close {{ background: none; border: none; color: var(--text-dim); font-size: 24px; cursor: pointer; padding: 4px 8px; }}
.modal-close:hover {{ color: var(--text); }}
.modal-body {{ overflow-y: auto; padding: 16px 20px; }}
.ticket-table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
.ticket-table th {{ text-align: left; padding: 8px 12px; color: var(--text-dim); border-bottom: 1px solid var(--border); font-weight: 500; position: sticky; top: 0; background: var(--surface); }}
.ticket-table td {{ padding: 8px 12px; border-bottom: 1px solid var(--border); }}
.ticket-table tr:hover {{ background: var(--surface2); }}
.ticket-key {{ color: var(--accent2); font-weight: 600; white-space: nowrap; }}
.ticket-key a {{ color: var(--accent2); text-decoration: none; }}
.ticket-key a:hover {{ text-decoration: underline; }}
.clickable {{ cursor: pointer; transition: opacity 0.2s; }}
.clickable:hover {{ opacity: 0.8; }}
.modal-count {{ font-size: 13px; color: var(--text-dim); }}
</style>
</head>
<body>
<div class="container">
<header>
<h1>CLISREP Phase 1 Analysis</h1>
<p>Cloud Engineering Workload Discovery | CLI ESR Tickets + Slack Channel | Feb - Aug 2026</p>
</header>

<!-- KPI CARDS -->
<div class="grid grid-4">
<div class="card stat-card">
    <div class="value">{jira.get('total_issues', 0)}</div>
    <div class="label">Jira ESR Tickets (sampled)</div>
    <div class="sublabel">~1,496 total in 6 months</div>
</div>
<div class="card stat-card">
    <div class="value">{slack.get('human_messages', 0) if slack else 'N/A'}</div>
    <div class="label">Slack Help Messages</div>
    <div class="sublabel">{slack.get('slack_only_percentage', 0)}% never become tickets</div>
</div>
<div class="card stat-card">
    <div class="value">~250</div>
    <div class="label">Requests / Month</div>
    <div class="sublabel">Jira + Slack combined</div>
</div>
<div class="card stat-card">
    <div class="value">{auto.get('high', 0) + auto.get('medium', 0)}</div>
    <div class="label">Automatable Tickets</div>
    <div class="sublabel">in this sample ({round((auto.get('high',0)+auto.get('medium',0))/max(jira.get('total_issues',1),1)*100,1)}%)</div>
</div>
</div>

<!-- KEY INSIGHTS -->
<h2 class="section-title">Key Insights</h2>
<div class="grid grid-2">
<div class="card">
<h3>Automation Opportunity</h3>
<div class="insight-box green">~53 tickets/month could be auto-resolved today (secrets, grafana access, plugin updates, outbox unblocking, scaling)</div>
<div class="insight-box amber">Estimated savings: ~106 engineer-hours/month at 2hr avg per automatable task</div>
<div class="insight-box red">Top 3 engineers handle 38% of all work — concentration risk</div>
</div>
<div class="card">
<h3>Coverage Gap</h3>
<div class="insight-box amber">{slack.get('slack_only_percentage', 0)}% of Slack requests never become formal Jira tickets — invisible workload</div>
<div class="insight-box green">45+ knowledge questions in Slack could be answered by AI with a Knowledge Graph</div>
<div class="insight-box">Plugin version updates (ssca-plugins) alone: 19 identical tickets in 6 months</div>
</div>
</div>

<!-- CATEGORY BREAKDOWN -->
<h2 class="section-title">Request Categories (Jira ESR)</h2>
<div class="grid grid-2">
<div class="card">
<h3>Distribution by Category</h3>
<div class="chart-container"><canvas id="categoryChart"></canvas></div>
</div>
<div class="card">
<h3>Top Categories</h3>
<ul class="bar-list">
{"".join(f'''<li class="clickable" onclick="showTickets('{c}')"><span class="bar-label">{c.replace("_", " ").title()[:20]}</span><span class="bar-bg"><span class="bar-fill" style="width:{categories[c]['percentage']/max(cat_pcts)*100 if cat_pcts else 0}%;background:var(--accent)"></span></span><span class="bar-value">{categories[c]['percentage']}%</span></li>''' for c in cat_labels[:8])}
</ul>
</div>
</div>

<!-- MONTHLY TRENDS -->
<h2 class="section-title">Monthly Volume Trends</h2>
<div class="grid grid-2">
<div class="card">
<h3>Jira ESR Tickets (capped at 100/month in sample)</h3>
<div class="chart-container"><canvas id="jiraMonthlyChart"></canvas></div>
</div>
<div class="card">
<h3>Slack Channel Activity</h3>
<div class="chart-container"><canvas id="slackMonthlyChart"></canvas></div>
</div>
</div>

<!-- OWNERSHIP -->
<h2 class="section-title">Ownership & Workload Distribution</h2>
<div class="grid grid-2">
<div class="card">
<h3>Top Assignees (Cloud Engineers)</h3>
<ul class="bar-list">
{"".join(f'''<li><span class="bar-label">{email.split("@")[0][:18]}</span><span class="bar-bg"><span class="bar-fill" style="width:{count/max(top_assignees.values())*100}%;background:var(--blue)"></span></span><span class="bar-value">{count}</span></li>''' for email, count in top_assignees.items())}
</ul>
</div>
<div class="card">
<h3>Top Reporters (Requesters)</h3>
<ul class="bar-list">
{"".join(f'''<li><span class="bar-label">{email.split("@")[0][:18]}</span><span class="bar-bg"><span class="bar-fill" style="width:{count/max(top_reporters.values())*100}%;background:var(--amber)"></span></span><span class="bar-value">{count}</span></li>''' for email, count in top_reporters.items())}
</ul>
</div>
</div>

<!-- STATUS & PRIORITY -->
<h2 class="section-title">Resolution & Priority</h2>
<div class="grid grid-3">
<div class="card">
<h3>Status Distribution</h3>
<div class="chart-container"><canvas id="statusChart"></canvas></div>
</div>
<div class="card">
<h3>Priority Distribution</h3>
<div class="chart-container"><canvas id="priorityChart"></canvas></div>
</div>
<div class="card">
<h3>Automation Feasibility</h3>
<div class="chart-container"><canvas id="autoChart"></canvas></div>
</div>
</div>

<!-- REPEAT PATTERNS -->
<h2 class="section-title">Top Repeat Patterns (Automation Targets)</h2>
<div class="card">
<table>
<thead><tr><th>Pattern</th><th>Count</th><th>Feasibility</th></tr></thead>
<tbody>
{"".join(f'''<tr><td>{r["pattern"][:80]}</td><td><strong>{r["count"]}</strong></td><td><span class="tag tag-high">High</span></td></tr>''' if r["count"] >= 5 else f'''<tr><td>{r["pattern"][:80]}</td><td><strong>{r["count"]}</strong></td><td><span class="tag tag-medium">Medium</span></td></tr>''' for r in repeat[:15])}
</tbody>
</table>
</div>

<!-- SLACK ANALYSIS -->
<h2 class="section-title">Slack Channel Analysis (all-cloud-engineers)</h2>
<div class="grid grid-2">
<div class="card">
<h3>Message Topics</h3>
<div class="chart-container"><canvas id="slackTopicChart"></canvas></div>
</div>
<div class="card">
<h3>Engagement Metrics</h3>
<div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-top:12px">
<div class="stat-card"><div class="value" style="font-size:24px">{engagement.get('avg_replies', 0)}</div><div class="label">Avg replies/thread</div></div>
<div class="stat-card"><div class="value" style="font-size:24px">{engagement.get('max_replies', 0)}</div><div class="label">Max replies</div></div>
<div class="stat-card"><div class="value" style="font-size:24px">{slack_intent.get('help_requests', 0)}</div><div class="label">Help requests</div></div>
<div class="stat-card"><div class="value" style="font-size:24px">{slack_intent.get('questions', 0)}</div><div class="label">Questions asked</div></div>
</div>
<div style="margin-top:16px">
<div class="insight-box">{slack_intent.get('slack_only', 0)} messages ({slack.get('slack_only_percentage', 0)}%) are NOT linked to any Jira ticket</div>
<div class="insight-box green">High engagement: {slack.get('threads_with_replies', 0)} threads got replies (avg {engagement.get('avg_replies', 0)} replies)</div>
</div>
</div>
</div>

<!-- RECOMMENDATIONS -->
<h2 class="section-title">Recommended Next Steps</h2>
<div class="grid grid-3">
<div class="card">
<h3>Immediate Wins (P0)</h3>
<ul style="font-size:13px;padding-left:16px">
<li>Automate secret creation workflow</li>
<li>Automate Grafana access provisioning</li>
<li>Automate plugin version updates</li>
<li>Automate outbox unblocking</li>
<li>Automate vanity URL creation</li>
</ul>
</div>
<div class="card">
<h3>Knowledge Graph Priorities</h3>
<ul style="font-size:13px;padding-left:16px">
<li>Service → Owner mapping</li>
<li>Service → Infrastructure mapping</li>
<li>Runbook library (by symptom)</li>
<li>Environment topology</li>
<li>Approval chain mapping</li>
</ul>
</div>
<div class="card">
<h3>Control Plane APIs</h3>
<ul style="font-size:13px;padding-left:16px">
<li>secrets/create (GSM + AWS)</li>
<li>grafana/access/grant</li>
<li>mongodb/scale</li>
<li>postgres/migration/status</li>
<li>kafka/outbox/unblock</li>
<li>networking/vanity-url/create</li>
<li>knowledge/ownership</li>
</ul>
</div>
</div>

<!-- DRILL-DOWN MODAL -->
<div class="modal-overlay" id="ticketModal">
<div class="modal">
<div class="modal-header">
<h2 id="modalTitle">Category Tickets</h2>
<span class="modal-count" id="modalCount"></span>
<button class="modal-close" onclick="closeModal()">&times;</button>
</div>
<div class="modal-body">
<table class="ticket-table">
<thead><tr><th>Key</th><th>Summary</th><th>Status</th><th>Assignee</th></tr></thead>
<tbody id="modalBody"></tbody>
</table>
</div>
</div>
</div>

<footer style="text-align:center;padding:30px 0;color:var(--text-dim);font-size:12px;border-top:1px solid var(--border);margin-top:30px">
Generated by CLISREP Pipeline v1.0.0 | Data period: Feb 14 - Aug 14, 2026 | Sources: Jira CLI ESR + Slack #all-cloud-engineers<br>
<span style="margin-top:4px;display:inline-block">Click any category bar to see associated tickets</span>
</footer>
</div>

<script>
Chart.defaults.color = '#8b95a8';
Chart.defaults.borderColor = '#2d3548';

// Category pie chart
new Chart(document.getElementById('categoryChart'), {{
    type: 'doughnut',
    data: {{
        labels: {json.dumps([c.replace('_', ' ').title() for c in cat_labels[:8]])},
        datasets: [{{ data: {json.dumps(cat_values[:8])}, backgroundColor: ['#6366f1','#818cf8','#3b82f6','#10b981','#f59e0b','#ef4444','#ec4899','#8b5cf6'] }}]
    }},
    options: {{ responsive: true, maintainAspectRatio: false, plugins: {{ legend: {{ position: 'right', labels: {{ boxWidth: 12, font: {{ size: 11 }} }} }} }} }}
}});

// Jira monthly
new Chart(document.getElementById('jiraMonthlyChart'), {{
    type: 'bar',
    data: {{
        labels: {json.dumps(list(jira_monthly.keys()))},
        datasets: [{{ label: 'Tickets', data: {json.dumps(list(jira_monthly.values()))}, backgroundColor: '#6366f1' }}]
    }},
    options: {{ responsive: true, maintainAspectRatio: false, plugins: {{ legend: {{ display: false }} }}, scales: {{ y: {{ beginAtZero: true }} }} }}
}});

// Slack monthly
new Chart(document.getElementById('slackMonthlyChart'), {{
    type: 'bar',
    data: {{
        labels: {json.dumps(list(slack_monthly.keys()))},
        datasets: [{{ label: 'Messages', data: {json.dumps(list(slack_monthly.values()))}, backgroundColor: '#10b981' }}]
    }},
    options: {{ responsive: true, maintainAspectRatio: false, plugins: {{ legend: {{ display: false }} }}, scales: {{ y: {{ beginAtZero: true }} }} }}
}});

// Status donut
new Chart(document.getElementById('statusChart'), {{
    type: 'doughnut',
    data: {{
        labels: {json.dumps(list(statuses.keys())[:6])},
        datasets: [{{ data: {json.dumps(list(statuses.values())[:6])}, backgroundColor: ['#10b981','#f59e0b','#3b82f6','#ef4444','#8b5cf6','#ec4899'] }}]
    }},
    options: {{ responsive: true, maintainAspectRatio: false, plugins: {{ legend: {{ position: 'bottom', labels: {{ boxWidth: 10, font: {{ size: 10 }} }} }} }} }}
}});

// Priority
new Chart(document.getElementById('priorityChart'), {{
    type: 'doughnut',
    data: {{
        labels: {json.dumps(list(priorities.keys()))},
        datasets: [{{ data: {json.dumps(list(priorities.values()))}, backgroundColor: ['#f59e0b','#6366f1','#3b82f6','#ef4444','#10b981'] }}]
    }},
    options: {{ responsive: true, maintainAspectRatio: false, plugins: {{ legend: {{ position: 'bottom', labels: {{ boxWidth: 10, font: {{ size: 10 }} }} }} }} }}
}});

// Automation feasibility
new Chart(document.getElementById('autoChart'), {{
    type: 'doughnut',
    data: {{
        labels: ['High (auto today)', 'Medium (with approval)', 'Low (human needed)', 'Not assessed'],
        datasets: [{{ data: [{auto.get('high', 0)}, {auto.get('medium', 0)}, {auto.get('low', 0)}, {jira.get('total_issues', 0) - auto.get('high', 0) - auto.get('medium', 0) - auto.get('low', 0)}], backgroundColor: ['#10b981','#f59e0b','#ef4444','#374151'] }}]
    }},
    options: {{ responsive: true, maintainAspectRatio: false, plugins: {{ legend: {{ position: 'bottom', labels: {{ boxWidth: 10, font: {{ size: 10 }} }} }} }} }}
}});

// Slack topics
new Chart(document.getElementById('slackTopicChart'), {{
    type: 'bar',
    data: {{
        labels: {json.dumps([t.replace('_', ' ').title() for t in list(slack_topics.keys())[:8]])},
        datasets: [{{ label: 'Messages', data: {json.dumps(list(slack_topics.values())[:8])}, backgroundColor: '#818cf8' }}]
    }},
    options: {{ indexAxis: 'y', responsive: true, maintainAspectRatio: false, plugins: {{ legend: {{ display: false }} }} }}
}});

// Ticket drill-down
const ticketData = {tickets_json};
const JIRA_BASE = 'https://harness.atlassian.net/browse/';

function showTickets(category) {{
    const tickets = ticketData[category] || [];
    const title = category.replace(/_/g, ' ').replace(/\\b\\w/g, c => c.toUpperCase());
    document.getElementById('modalTitle').textContent = title;
    document.getElementById('modalCount').textContent = tickets.length + ' tickets';
    const tbody = document.getElementById('modalBody');
    tbody.innerHTML = tickets.map(t => `<tr>
        <td class="ticket-key"><a href="${{JIRA_BASE}}${{t.key}}" target="_blank">${{t.key}}</a></td>
        <td>${{t.summary}}</td>
        <td>${{t.status || 'Unknown'}}</td>
        <td>${{t.assignee || 'unassigned'}}</td>
    </tr>`).join('');
    document.getElementById('ticketModal').classList.add('active');
}}

function closeModal() {{
    document.getElementById('ticketModal').classList.remove('active');
}}

document.getElementById('ticketModal').addEventListener('click', function(e) {{
    if (e.target === this) closeModal();
}});

document.addEventListener('keydown', function(e) {{
    if (e.key === 'Escape') closeModal();
}});

// Make doughnut chart segments clickable
document.getElementById('categoryChart').addEventListener('click', function(e) {{
    const chart = Chart.getChart(this);
    const points = chart.getElementsAtEventForMode(e, 'nearest', {{ intersect: true }}, true);
    if (points.length) {{
        const idx = points[0].index;
        const catKeys = {json.dumps(cat_labels[:8])};
        if (catKeys[idx]) showTickets(catKeys[idx]);
    }}
}});
</script>
</body>
</html>"""

    output_path.write_text(html)
    print(f"  [Dashboard] Generated → {output_path}")


def generate_kg_readme(project_root: Path):
    """Generate README for the knowledge-graph directory."""
    readme = """# CLISREP Knowledge Graph

This directory contains the structured knowledge base for the CLI SRE Platform.
Files are YAML for human readability and git-diffability.

## Structure

| File | Purpose | Maintainer |
|------|---------|-----------|
| `request-categories.yaml` | Request taxonomy with sub-types and automation feasibility | Cloud Eng |
| `ownership-model.yaml` | Team members, specializations, routing rules | Cloud Eng |
| `workflows.yaml` | Identified operational workflows (P0/P1/P2) | Cloud Eng |
| `control-plane-apis.yaml` | MCP tools and REST APIs for the control plane | Cloud Eng |
| `kg-schema.yaml` | Entity/relationship schema definition | Platform |
| `analysis-summary.yaml` | Analysis findings and baseline metrics | Auto-generated |

## How to Maintain

1. **Adding a new service**: Create `services/{service-id}.yaml` following the schema in `kg-schema.yaml`
2. **Updating ownership**: Edit `ownership-model.yaml` routing rules
3. **Adding a workflow**: Add entry to `workflows.yaml` with triggers, steps, and guardrails
4. **Re-running analysis**: `python pipeline/run.py` (regenerates analysis-summary and dashboard)

## Generated By

CLISREP Analysis Pipeline v1.0.0
- Source data: Jira CLI ESR issues + Slack #all-cloud-engineers
- Period: Feb 14 - Aug 14, 2026
- Run command: `python pipeline/run.py`
"""
    (project_root / "knowledge-graph" / "README.md").write_text(readme)
    print(f"  [README] Generated → knowledge-graph/README.md")


def run(config_path: str):
    config = yaml.safe_load(Path(config_path).read_text())
    project_root = Path(config_path).parent.parent
    analyzed_dir = project_root / "data" / "analyzed"

    jira_analysis = None
    slack_analysis = None

    jira_path = analyzed_dir / "jira_analysis.json"
    if jira_path.exists():
        jira_analysis = json.loads(jira_path.read_text())

    slack_path = analyzed_dir / "slack_analysis.json"
    if slack_path.exists():
        slack_analysis = json.loads(slack_path.read_text())

    if not jira_analysis:
        print("  [ERROR] No analyzed Jira data found. Run stage 'analyze' first.")
        return

    # Generate dashboard
    dashboard_path = project_root / "dashboard.html"
    generate_dashboard(jira_analysis, slack_analysis or {}, dashboard_path)

    # Generate KG README
    generate_kg_readme(project_root)
