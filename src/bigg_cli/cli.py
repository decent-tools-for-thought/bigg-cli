"""Argument parser and command dispatch for bigg-cli."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Never

from .client import BiggApiClient, ClientSettings
from .config import load_config
from .core import (
    op_api_get,
    op_model_gene,
    op_model_genes,
    op_model_metabolite,
    op_model_metabolites,
    op_model_reaction,
    op_model_reactions,
    op_models_download,
    op_models_list,
    op_models_show,
    op_search,
    op_universal_metabolite,
    op_universal_metabolites,
    op_universal_reaction,
    op_universal_reactions,
    op_version,
    render_output,
    write_download,
)
from .errors import ApiError, BiggError, ConfigError, UsageError
from .types import JsonData


class _HelpParser(argparse.ArgumentParser):
    def error(self, message: str) -> Never:
        raise UsageError(message)


def _add_common_global_flags(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--base-url",
        help="BiGG API base URL (default: https://bigg.ucsd.edu)",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        help="Request timeout in seconds",
    )
    parser.add_argument(
        "--output",
        choices=("text", "json", "jsonl"),
        help="Output format (text|json|jsonl)",
    )
    parser.add_argument(
        "--config",
        type=Path,
        help="Optional path to config TOML file",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = _HelpParser(
        prog="bigg",
        description="Command-line interface for the BiGG Models API",
    )
    _add_common_global_flags(parser)

    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("version", help="Show BiGG database/API version")

    search = subparsers.add_parser("search", help="Search models, reactions, metabolites, or genes")
    search.add_argument("query", help="Search query text")
    search.add_argument(
        "--type",
        dest="search_type",
        default="models",
        choices=("models", "reactions", "metabolites", "genes"),
        help="Search type",
    )
    search.add_argument("--limit", type=int, help="Limit number of search results")

    models = subparsers.add_parser("models", help="Model-centric BiGG operations")
    models_sub = models.add_subparsers(dest="models_command", required=True)

    models_list = models_sub.add_parser("list", help="List available models")
    models_list.add_argument("--limit", type=int, help="Limit listed models")

    models_show = models_sub.add_parser("show", help="Show metadata for one model")
    models_show.add_argument("model_id", help="Model BiGG ID")

    models_download = models_sub.add_parser("download", help="Download model JSON")
    models_download.add_argument("model_id", help="Model BiGG ID")
    models_download.add_argument(
        "--out",
        type=Path,
        help="Output file path (default: <model_id>.json)",
    )

    models_reactions = models_sub.add_parser("reactions", help="List reactions for model")
    models_reactions.add_argument("model_id", help="Model BiGG ID")
    models_reactions.add_argument("--limit", type=int, help="Limit listed reactions")

    models_reaction = models_sub.add_parser("reaction", help="Show one model reaction")
    models_reaction.add_argument("model_id", help="Model BiGG ID")
    models_reaction.add_argument("reaction_id", help="Reaction BiGG ID")

    models_metabolites = models_sub.add_parser("metabolites", help="List metabolites for model")
    models_metabolites.add_argument("model_id", help="Model BiGG ID")
    models_metabolites.add_argument("--limit", type=int, help="Limit listed metabolites")

    models_metabolite = models_sub.add_parser("metabolite", help="Show one model metabolite")
    models_metabolite.add_argument("model_id", help="Model BiGG ID")
    models_metabolite.add_argument("metabolite_id", help="Model metabolite ID, e.g. 10fthf_c")

    models_genes = models_sub.add_parser("genes", help="List genes for model")
    models_genes.add_argument("model_id", help="Model BiGG ID")
    models_genes.add_argument("--limit", type=int, help="Limit listed genes")

    models_gene = models_sub.add_parser("gene", help="Show one model gene")
    models_gene.add_argument("model_id", help="Model BiGG ID")
    models_gene.add_argument("gene_id", help="Gene BiGG ID")

    universal = subparsers.add_parser("universal", help="Universal namespace operations")
    universal_sub = universal.add_subparsers(dest="universal_command", required=True)

    universal_reactions = universal_sub.add_parser("reactions", help="List universal reactions")
    universal_reactions.add_argument("--limit", type=int, help="Limit listed reactions")

    universal_reaction = universal_sub.add_parser("reaction", help="Show one universal reaction")
    universal_reaction.add_argument("reaction_id", help="Reaction BiGG ID")

    universal_metabolites = universal_sub.add_parser(
        "metabolites", help="List universal metabolites"
    )
    universal_metabolites.add_argument("--limit", type=int, help="Limit listed metabolites")

    universal_metabolite = universal_sub.add_parser(
        "metabolite", help="Show one universal metabolite"
    )
    universal_metabolite.add_argument("metabolite_id", help="Metabolite BiGG ID")

    api = subparsers.add_parser("api", help="Direct API escape hatch")
    api_sub = api.add_subparsers(dest="api_command", required=True)
    api_get = api_sub.add_parser("get", help="Direct GET by absolute path")
    api_get.add_argument("path", help="Absolute path such as /api/v2/models")
    api_get.add_argument(
        "--query",
        action="append",
        default=[],
        metavar="KEY=VALUE",
        help="Query parameter, repeatable",
    )

    return parser


def _resolve_config(args: argparse.Namespace) -> tuple[str, float, str]:
    cfg = load_config(
        cli_base_url=args.base_url,
        cli_timeout=args.timeout,
        cli_output=args.output,
        config_path=args.config,
    )
    return cfg.base_url, cfg.timeout, cfg.output


def _print_rendered(data: JsonData, *, output: str, context: str) -> int:
    rendered = render_output(data, output=output, context=context)
    if rendered.content:
        print(rendered.content)
    return 0


def dispatch(args: argparse.Namespace) -> int:
    base_url, timeout, output = _resolve_config(args)
    if args.command is None:
        return 0

    settings = ClientSettings(base_url=base_url, timeout=timeout)
    with BiggApiClient(settings) as client:
        command = args.command
        if command == "version":
            return _print_rendered(op_version(client), output=output, context="version")

        if command == "search":
            data = op_search(
                client,
                query=args.query,
                search_type=args.search_type,
                limit=args.limit,
            )
            return _print_rendered(data, output=output, context="search")

        if command == "models":
            sub = args.models_command
            if sub == "list":
                return _print_rendered(
                    op_models_list(client, limit=args.limit),
                    output=output,
                    context="models.list",
                )
            if sub == "show":
                return _print_rendered(
                    op_models_show(client, model_id=args.model_id),
                    output=output,
                    context="models.show",
                )
            if sub == "download":
                model = op_models_download(client, model_id=args.model_id)
                out_path = args.out or Path(f"{args.model_id}.json")
                write_download(out_path, model)
                if output == "text":
                    print(f"Saved model JSON to {out_path}")
                return 0
            if sub == "reactions":
                return _print_rendered(
                    op_model_reactions(client, model_id=args.model_id, limit=args.limit),
                    output=output,
                    context="models.reactions.list",
                )
            if sub == "reaction":
                return _print_rendered(
                    op_model_reaction(client, model_id=args.model_id, reaction_id=args.reaction_id),
                    output=output,
                    context="models.reaction",
                )
            if sub == "metabolites":
                return _print_rendered(
                    op_model_metabolites(client, model_id=args.model_id, limit=args.limit),
                    output=output,
                    context="models.metabolites.list",
                )
            if sub == "metabolite":
                return _print_rendered(
                    op_model_metabolite(
                        client,
                        model_id=args.model_id,
                        metabolite_id=args.metabolite_id,
                    ),
                    output=output,
                    context="models.metabolite",
                )
            if sub == "genes":
                return _print_rendered(
                    op_model_genes(client, model_id=args.model_id, limit=args.limit),
                    output=output,
                    context="models.genes.list",
                )
            if sub == "gene":
                return _print_rendered(
                    op_model_gene(client, model_id=args.model_id, gene_id=args.gene_id),
                    output=output,
                    context="models.gene",
                )

        if command == "universal":
            sub = args.universal_command
            if sub == "reactions":
                return _print_rendered(
                    op_universal_reactions(client, limit=args.limit),
                    output=output,
                    context="universal.reactions.list",
                )
            if sub == "reaction":
                return _print_rendered(
                    op_universal_reaction(client, reaction_id=args.reaction_id),
                    output=output,
                    context="universal.reaction",
                )
            if sub == "metabolites":
                return _print_rendered(
                    op_universal_metabolites(client, limit=args.limit),
                    output=output,
                    context="universal.metabolites.list",
                )
            if sub == "metabolite":
                return _print_rendered(
                    op_universal_metabolite(client, metabolite_id=args.metabolite_id),
                    output=output,
                    context="universal.metabolite",
                )

        if command == "api" and args.api_command == "get":
            api_data: JsonData = op_api_get(client, path=args.path, query=args.query)
            return _print_rendered(api_data, output=output, context="api.get")

    raise UsageError("Unrecognized command combination")


def run(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args_list = list(argv) if argv is not None else sys.argv[1:]

    if not args_list:
        parser.print_help()
        return 0

    try:
        args = parser.parse_args(args_list)
        return dispatch(args)
    except SystemExit as exc:
        # argparse emits SystemExit(0) for --help; keep it as a normal successful return.
        return int(exc.code) if isinstance(exc.code, int) else 0
    except (UsageError, ConfigError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2
    except (ApiError, BiggError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
