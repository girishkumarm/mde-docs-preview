# Market Data Engine — Documentation (Mintlify)

Mintlify docs site for the **Paytm Money — Market Data Engine** (v3.2).
Source-of-truth Confluence parent: [Market Data Engine — Technical Design Document](https://paytmmoney.atlassian.net/wiki/spaces/PM/pages/683246061).

## Run it locally

```bash
# one-time install (Node 18+)
npm i -g mint

# from this directory
mint dev
```

Opens at http://localhost:3000.

## Structure

```
.
├── docs.json                    # Mintlify config + navigation
├── introduction.mdx             # Landing page (root TDD)
├── architecture/
│   ├── overview.mdx             # High-level architecture synthesis
│   └── diagrams.mdx             # Decision + system diagrams (SVG + Excalidraw)
├── decisions/
│   └── kafka-vs-redis.mdx       # ADR: why Kafka AND Redis, not one-or-the-other
├── components/
│   ├── part1-feed-to-charts.mdx # Feed handler, snapshot, charts (legacy context)
│   ├── part2-fno-movers-alerts.mdx # FNO, market movers, alerts, ops (incl. v3.2 resilience + AI IM)
│   ├── candles-v2.mdx           # CURRENT: dual-sink writer, Redis running, ClickHouse closed
│   └── candles-v2-diagrams.mdx  # Diagram download pointers
├── data-apis/
│   └── data-models-and-apis.mdx # Data models, public APIs, scheduled jobs
├── operations/
│   ├── devops-guide.mdx         # Staging provisioning + monthly AWS cost
│   ├── v2-production-readiness.mdx
│   ├── v2-oncall-runbook.mdx
│   ├── candles-v2-readiness.mdx
│   └── candles-v2-canary-rollback.mdx
├── migration/
│   ├── overview.mdx             # Cut-over plan (5 deployment groups)
│   └── price-engine.mdx         # Detailed sub-doc
├── images/                      # All diagrams: SVG + PNG + Excalidraw sources
│   ├── 683246061/               # Attached to root TDD
│   ├── 683278403/               # Components Part 2
│   ├── 683278423/               # Data Models
│   ├── 683376743/               # Operations/Deployment/Migration
│   ├── 683475046/               # Components Part 1
│   └── 693502030/               # Architecture Diagrams page
├── _raw/                        # Source HTML from Confluence + convert.py (kept for re-import)
├── _attachments/                # Original attachment backups
└── _converted/                  # First-pass MDX (pre-organization)
```

## Hybrid diagram policy

- **SVG / PNG**: complex architecture, topology, decision diagrams — authored in Excalidraw, exported as SVG, attached inline.
- **Mermaid**: flows, sequences, cut-over paths — live in MDX, editable inline. Current Mermaid diagrams live in:
  - [architecture/overview.mdx](architecture/overview.mdx) — system flow
  - [architecture/diagrams.mdx](architecture/diagrams.mdx) — resilience layers composition
  - [components/candles-v2.mdx](components/candles-v2.mdx) — dual-sink write + read paths
  - [migration/overview.mdx](migration/overview.mdx) — legacy → v3.2 cut-over

## Editing a diagram

For Excalidraw-authored SVGs under `images/693502030/`:

1. Download the `.excalidraw` file from the same directory.
2. Open https://excalidraw.com, drag-and-drop the file onto the canvas.
3. Edit.
4. Export as SVG, replace the file in `images/693502030/`, commit.

For Mermaid diagrams, just edit the ` ```mermaid ` fenced code block in the MDX page.

## Re-importing from Confluence

If Confluence updates and you want to refresh:

```bash
# requires girish3.kumar@paytm.com Atlassian API token in $CONF_TOKEN
cd _raw
python3 convert.py
# then copy converted .mdx into the target sections as appropriate
```

The `convert.py` script maps Confluence `ac:structured-macro` (info/warning/note/code/expand/panel) to Mintlify components (`<Info>`, `<Warning>`, `<Note>`, `<Accordion>`, fenced code blocks) and preserves tables, lists, and cross-links.

## Inconsistency fixes applied during the initial import

The Confluence source tree had a handful of stale sections because individual pages were updated at different times. The following were corrected during the Mintlify conversion:

| Where | What was stale | Fix |
| --- | --- | --- |
| `architecture/diagrams.mdx` | Index table only listed D1–D6 but the page contained D1–D8, D11, D12 | Rewrote index to match actual diagrams; documented the D9/D10 gap |
| `architecture/diagrams.mdx` | D7 (TimescaleDB) was presented as accepted | Added explicit **Superseded** banner — ClickHouse replaced TimescaleDB in v3.1 |
| `migration/overview.mdx` | Technology Stack table still listed TimescaleDB as current and Charts Data Collector as a live service | Prepended a **Warning** banner directing readers to `candles-v2.mdx` and `devops-guide.mdx` for the authoritative v3.2 storage layout |

Original Confluence content is preserved verbatim in `_converted/` for audit.

## Deploying to mintlify.com

1. Create a repo on GitHub / Bitbucket, push this directory.
2. Log in at https://mintlify.com, connect the repo.
3. Set the docs root to this repo's root (where `docs.json` lives).
4. Auto-deploy on every push.

## Maintenance owner

- **Primary**: girish3.kumar@paytm.com
- **Confluence parent**: paytmmoney.atlassian.net/wiki/spaces/PM/pages/683246061
