# bigg-cli

`bigg` is a production-ready command-line client for the [BiGG Models API](http://bigg.ucsd.edu/data_access), built for scripted and interactive access to models, reactions, metabolites, genes, and search workflows.

## Install

From source (editable):

```bash
python -m pip install -e .
```

Standard install:

```bash
python -m pip install .
```

## Quick Start

Show top-level help:

```bash
bigg
bigg --help
bigg docs
```

Get database version:

```bash
bigg version
bigg version --output json
```

List models and filter output:

```bash
bigg models list --limit 5
bigg models list --output json
```

Look up details:

```bash
bigg models show iND750
bigg models reaction iND750 GAPD
bigg models metabolite iND750 10fthf_c
bigg models gene iMM904 Q0045
bigg show iND750
```

Search the catalog:

```bash
bigg search g3p --type metabolites
bigg search iJO1366 --type models --output json
```

Universal namespace:

```bash
bigg universal reactions --limit 10
bigg universal reaction ADA
bigg universal metabolite g3p
bigg universal where-reaction ADA
bigg universal where-metabolite g3p

Download static model files and namespace resources:

```bash
bigg models download-static iMM904 --format xml
bigg models download-static iMM904 --format mat --out iMM904.mat
bigg namespace reactions
bigg namespace metabolites
bigg namespace universal-model
```
```

Generic API escape hatch:

```bash
bigg api get /api/v2/models/iND750
bigg api get /api/v2/search --query query=g3p --query search_type=metabolites

Additional analysis workflows:

```bash
bigg compare models iJO1366 iML1515
bigg where gene gapA
bigg links reaction ADA
bigg batch show model --id iJO1366 --id iML1515
```

## Command Surface

- `version`: BiGG database/API version.
- `docs`: Generated documentation for all available commands and usage.
- `search`: Query API search endpoint (`models|reactions|metabolites|genes`).
- `find <query>`: Search all resource families in one call.
- `show <id>`: Resolve an ID across model/universal resources.
- `where gene <gene_id>`: Find matching genes across models.
- `compare models <a> <b>`: Compare overlap and differences.
- `links <resource> <id> [--model-id ...]`: Flatten external database links.
- `batch show <resource> --id ... [--from-file ...]`: Batch resource resolution.
- `models`:
  - `list`
  - `show <model_id>`
  - `summary <model_id>`
  - `download <model_id>`
  - `download-static <model_id> --format xml|xml.gz|json|mat`
  - `reactions <model_id>` / `reaction <model_id> <reaction_id>`
  - `reaction-equation <model_id> <reaction_id>`
  - `metabolites <model_id>` / `metabolite <model_id> <metabolite_id>`
  - `genes <model_id>` / `gene <model_id> <gene_id>`
  - `exists <model_id> [--reaction ...] [--metabolite ...] [--gene ...]`
  - `export-ids <model_id> --type reactions|metabolites|genes`
  - `stats [--organism <pattern>]`
- `universal`:
  - `reactions` / `reaction <reaction_id>`
  - `metabolites` / `metabolite <metabolite_id>`
  - `where-reaction <reaction_id>`
  - `where-metabolite <metabolite_id>`
- `api get <path>`: Direct GET against API/static endpoints.
- `fetch <path-or-url>`: GET with optional field extraction.
- `namespace`:
  - `reactions`
  - `metabolites`
  - `universal-model`

## Output Modes

Global `--output` supports:

- `text` (default): concise, readable summaries and tabular list-style lines.
- `json`: full structured JSON response.
- `jsonl`: one record per line for list responses.

`jsonl` is valid only for list-like responses; scalar/object responses return a validation error.

## Configuration

Configuration precedence is explicit:

1. CLI flags
2. Environment variables
3. XDG config file
4. Built-in defaults

Supported settings:

- `base_url`
- `timeout`
- `output`

Environment variables:

- `BIGG_BASE_URL` (default: `https://bigg.ucsd.edu`)
- `BIGG_TIMEOUT` (seconds, default: `20`)
- `BIGG_OUTPUT` (`text|json|jsonl`, default: `text`)

Config file locations:

- `$XDG_CONFIG_HOME/bigg-cli/config.toml`
- `~/.config/bigg-cli/config.toml` (fallback)

Example `config.toml`:

```toml
base_url = "https://bigg.ucsd.edu"
timeout = 30
output = "text"
```

## Behavior and Errors

- Usage/config/validation errors exit with code `2`.
- Runtime/API/network failures exit nonzero (`1`).
- HTTP errors include endpoint, status, and concise details.
- JSON parse failures are reported clearly.
- Timeouts are explicit and configurable.

No auth is required for BiGG API v2.

## Development

Install dev dependencies:

```bash
python -m pip install -e ".[dev]"
```

Run checks:

```bash
ruff check .
mypy src tests
pytest
```

## API Caveats

- Respect upstream guidance to avoid high request rates (BiGG asks users not to exceed ~10 requests/second).
- API data shape can vary across endpoints; `--output json` is safest for downstream machine use.
- `models download` uses JSON endpoint `/api/v2/models/{id}/download` and writes raw JSON model data.
- Static model formats use `/static/models/{model_id}.{xml|xml.gz|json|mat}`.
- Namespace downloads use `/static/namespace/bigg_models_reactions.txt`, `/static/namespace/bigg_models_metabolites.txt`, and `/static/namespace/universal_model.json`.

## Attribution

This tool wraps the BiGG Models API provided by the Systems Biology Research Group (SBRG), UCSD.

Reference publication:
King ZA et al. (2016) *BiGG Models: A platform for integrating, standardizing, and sharing genome-scale models*.
