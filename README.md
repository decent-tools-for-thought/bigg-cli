<div align="center">

# bigg-cli

[![Release](https://img.shields.io/github/v/release/decent-tools-for-thought/bigg-cli?sort=semver&color=0f766e)](https://github.com/decent-tools-for-thought/bigg-cli/releases)
![Python](https://img.shields.io/badge/python-3.11%2B-0ea5e9)
![License](https://img.shields.io/badge/license-MIT-14b8a6)

Production-ready command-line client for the BiGG Models API, with model, universal, search, namespace, and analysis workflows from the shell.

</div>

> [!IMPORTANT]
> This codebase is entirely AI-generated. It is useful to me, I hope it might be useful to others, and issues and contributions are welcome.

## Map
- [Install](#install)
- [Functionality](#functionality)
- [Configuration](#configuration)
- [Quick Start](#quick-start)
- [Credits](#credits)

## Install
$$\color{#0EA5E9}Install \space \color{#14B8A6}Tool$$

```bash
python -m pip install .
bigg --help
```

For local development:

```bash
python -m pip install -e ".[dev]"
ruff check .
mypy src tests
pytest
```

## Functionality
$$\color{#0EA5E9}Model \space \color{#14B8A6}Browse$$
- `bigg models list|show|summary|download|download-static`: inspect and export BiGG models.
- `bigg models reactions|reaction|reaction-equation`: browse model reaction tables and one reaction in detail.
- `bigg models metabolites|metabolite`: browse model metabolite tables and one metabolite in detail.
- `bigg models genes|gene|exists|export-ids|stats`: inspect genes, presence checks, ID exports, and summary stats.

$$\color{#0EA5E9}Search \space \color{#14B8A6}Lookup$$
- `bigg search`: query the BiGG search endpoint by family.
- `bigg find <query>`: search across resource families in one call.
- `bigg show <id>`: resolve an identifier across model and universal resources.
- `bigg where gene <gene-id>`: find matching genes across models.
- `bigg compare models <a> <b>`: compare model overlap and differences.
- `bigg links <resource> <id>`: flatten cross-database links for one resource.
- `bigg batch show <resource> --id ...`: resolve many resources in one command.

$$\color{#0EA5E9}Universal \space \color{#14B8A6}Space$$
- `bigg universal reactions|reaction`: browse universal reactions.
- `bigg universal metabolites|metabolite`: browse universal metabolites.
- `bigg universal where-reaction|where-metabolite`: list model usage for one universal entity.

$$\color{#0EA5E9}Raw \space \color{#14B8A6}Access$$
- `bigg api get <path>`: direct GET against API and static endpoints.
- `bigg fetch <path-or-url>`: generic GET with optional field extraction.
- `bigg namespace reactions|metabolites|universal-model`: fetch static namespace resources.

## Configuration
$$\color{#0EA5E9}Save \space \color{#14B8A6}Defaults$$

Configuration precedence:

1. CLI flags
2. Environment variables
3. Config file
4. Built-in defaults

Supported settings:

- `BIGG_BASE_URL`
- `BIGG_TIMEOUT`
- `BIGG_OUTPUT`

Config files:

- `$XDG_CONFIG_HOME/bigg-cli/config.toml`
- `~/.config/bigg-cli/config.toml`

Example:

```toml
base_url = "http://bigg.ucsd.edu"
timeout = 30
output = "text"
```

No authentication is required for BiGG API v2.

## Quick Start
$$\color{#0EA5E9}Try \space \color{#14B8A6}Lookup$$

```bash
bigg version
bigg models list --limit 5
bigg models show iND750
bigg models reaction iND750 GAPD
bigg search g3p --type metabolites --output json
bigg universal reaction ADA
bigg namespace reactions
bigg compare models iJO1366 iML1515
```

## Credits

This client is built for the BiGG Models API and is not affiliated with BiGG Models or SBRG.

Credit goes to the Systems Biology Research Group and the BiGG Models maintainers for the database, API, and documentation this tool depends on.
