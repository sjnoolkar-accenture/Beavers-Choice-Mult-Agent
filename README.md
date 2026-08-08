# Beaver's Choice Multi-Agent System

Production-structured implementation of the Beaver's Choice Paper Company
inventory, quoting, and fulfillment exercise.

## Architecture

```text
Customer
   |
Orchestrator Agent
   |-- Inventory Agent --> InventoryService --> SQLite repositories
   |-- Quoting Agent ----> PricingService ----> quote history
   `-- Fulfillment Agent -> OrderService ------> atomic transaction
```

The system uses four `pydantic-ai` agents and deterministic services for
financial and inventory decisions. The LLM layer cannot invent prices, stock,
products, quantities, or delivery dates.

## Project layout

```text
src/beavers_choice/
  agents.py          pydantic-ai agents and tools
  application.py     dependency-injection bootstrap
  database.py        SQLite lifecycle and schema
  repositories.py    persistence and reporting queries
  helpers.py         starter-compatible helper facade
  models.py          typed domain and API models
  services/          parsing, pricing, inventory, and atomic ordering
  evaluation.py      CSV evaluation harness
  diagram.py         workflow image generation
  cli.py             command-line entrypoint
tests/                regression and rubric tests
```

`beavers_choice_agents.py` remains as a compatibility launcher.

## Setup

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev,diagram]"
```

## Commands

```powershell
# Evaluate the supplied dataset
beavers-choice --evaluate quote_requests_sample.csv --reset

# Process one request
beavers-choice --request "Quote 500 sheets of glossy paper by April 15, 2025." `
  --date 2025-04-08

# Generate a report
beavers-choice --report 2025-05-15

# Regenerate the workflow
beavers-choice --diagram agent_workflow.png

# Run tests
python -m pytest
```

See `PROJECT_REPORT.md` for the design rationale and measured evaluation.
