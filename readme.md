# CLISREP

**CLI SRE Platform** — one stop solution for all your cloud doubts.

## Architecture

```mermaid
flowchart LR
    Dev([Dev]) --> Platform

    subgraph Platform
        Agent[Agent]
        CTN[Containers]
    end

    Agent --> KG
    KG --> Wf
    KG -. "<15% escalate" .-> NoWf([Human])
    Wf --> Control

    subgraph KG[Knowledge Graph]
        direction TB
        MD[".md files"]
        IntentMap["Intent → Wf mapping"]
    end

    subgraph Wf[Workflows]
        W1[Wf 1]
        W2[Wf 2]
        W3[Wf N]
    end

    subgraph Control[Control Plane]
        MCPs[MCPs / APIs]
        RO[Read-only MCPs]
    end

    Control --> Dynamic[Dynamic Mode]
    Dynamic --> Think["Agent Thinking\n(persona-based)"]
    Think --> Output([Output])

    KB[(KB\nvector-db)] --> Think
    KB -. "cj: every hour" .- Slack[Slack + Confluence]
    KG -. "cj: daily" .- Repos[Repos]

    Platform --> Probe[Probe] --> Manta[Manta Dashboard]
    Output --> CLI([CLI]) --> End([End User])
    End -. "feedback" .-> CLI
```

## Phase 1: Analysis — Complete

| | |
|---|---|
| **Jira tickets (6mo)** | ~1,496 |
| **Slack + Jira real requests** | 1,046 classified |
| **Automatable** | 61% (640 requests routable to handlers) |
| **Top intents** | provision_datastore 14%, rotate_secret 10%, grant_permission 7% |
| **Coverage** | 79% routed to specific intents (21% catch-all) |

## Next Steps

1. **Build 2 workflows** — `provision_datastore` and `rotate_secret` (highest volume intents)
2. **Build the Knowledge Graph** — repo-based `.md` files with intent-to-workflow mapping, daily cron updates
3. **KB (vector-db)** — ingest Slack + Confluence for knowledge questions, hourly cron sync

## Run

```sh
python pipeline/run.py
```

S1 Gather → S2 Analyze → S3 Generate (KG + Dashboard)

## Structure

```
pipeline/           # Reproducible 3-stage pipeline
data/raw/           # Jira + Slack source dumps
data/analyzed/      # Structured analysis + intent classification
knowledge-graph/    # Maintainable YAML (categories, ownership, workflows, APIs)
cc-dashboard.html   # Intent-based dashboard (presentation)
dashboard.html      # Domain-based dashboard (detailed)
```
