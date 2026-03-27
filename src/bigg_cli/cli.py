"""Argument parser and command dispatch for bigg-cli."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any, Never

from .client import BiggApiClient, ClientSettings
from .config import load_config
from .core import (
    op_api_get,
    op_fetch,
    op_find,
    op_model_export_ids,
    op_model_gene,
    op_model_genes,
    op_model_metabolite,
    op_model_metabolites,
    op_model_reaction,
    op_model_reaction_equation,
    op_model_reactions,
    op_model_stats,
    op_models_download,
    op_models_download_static,
    op_models_exists,
    op_models_list,
    op_models_show,
    op_models_summary,
    op_namespace_metabolites,
    op_namespace_reactions,
    op_namespace_universal_model,
    op_search,
    op_show,
    op_universal_metabolite,
    op_universal_metabolites,
    op_universal_reaction,
    op_universal_reactions,
    op_universal_where_metabolite,
    op_universal_where_reaction,
    op_version,
    render_output,
    write_bytes,
    write_download,
)
from .errors import ApiError, BiggError, ConfigError, UsageError
from .types import JsonData


class _HelpParser(argparse.ArgumentParser):
    def error(self, message: str) -> Never:
        raise UsageError(message)


def _add_common_global_flags(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--base-url", help="BiGG API base URL (default: https://bigg.ucsd.edu)")
    parser.add_argument("--timeout", type=float, help="Request timeout in seconds")
    parser.add_argument(
        "--output",
        choices=("text", "json", "jsonl"),
        help="Output format (text|json|jsonl)",
    )
    parser.add_argument("--config", type=Path, help="Optional path to config TOML file")


def _add_search_commands(subparsers: Any) -> None:
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

    find = subparsers.add_parser("find", help="Search all resource families at once")
    find.add_argument("query", help="Search query text")
    find.add_argument("--limit", type=int, help="Limit per resource type")

    show = subparsers.add_parser("show", help="Resolve a BiGG identifier across resources")
    show.add_argument("identifier", help="ID to resolve")


def _add_models_commands(subparsers: Any) -> None:
    models = subparsers.add_parser("models", help="Model-centric BiGG operations")
    models_sub = models.add_subparsers(dest="models_command", required=True)

    models_list = models_sub.add_parser("list", help="List available models")
    models_list.add_argument("--limit", type=int, help="Limit listed models")

    models_show = models_sub.add_parser("show", help="Show metadata for one model")
    models_show.add_argument("model_id", help="Model BiGG ID")

    models_summary = models_sub.add_parser("summary", help="High-level summary for one model")
    models_summary.add_argument("model_id", help="Model BiGG ID")

    models_download = models_sub.add_parser("download", help="Download model JSON")
    models_download.add_argument("model_id", help="Model BiGG ID")
    models_download.add_argument(
        "--out", type=Path, help="Output file path (default: <model_id>.json)"
    )

    models_download_static = models_sub.add_parser(
        "download-static", help="Download model from static format endpoint"
    )
    models_download_static.add_argument("model_id", help="Model BiGG ID")
    models_download_static.add_argument(
        "--format",
        dest="static_format",
        choices=("xml", "xml.gz", "json", "mat"),
        required=True,
        help="Static file format",
    )
    models_download_static.add_argument("--out", type=Path, help="Output file path")

    models_reactions = models_sub.add_parser("reactions", help="List reactions for model")
    models_reactions.add_argument("model_id", help="Model BiGG ID")
    models_reactions.add_argument("--limit", type=int, help="Limit listed reactions")

    models_reaction = models_sub.add_parser("reaction", help="Show one model reaction")
    models_reaction.add_argument("model_id", help="Model BiGG ID")
    models_reaction.add_argument("reaction_id", help="Reaction BiGG ID")

    models_reaction_equation = models_sub.add_parser(
        "reaction-equation", help="Render readable equation for model reaction"
    )
    models_reaction_equation.add_argument("model_id", help="Model BiGG ID")
    models_reaction_equation.add_argument("reaction_id", help="Reaction BiGG ID")

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

    models_exists = models_sub.add_parser("exists", help="Check model/resource existence")
    models_exists.add_argument("model_id", help="Model BiGG ID")
    models_exists.add_argument("--reaction", dest="reaction_id", help="Reaction ID to verify")
    models_exists.add_argument("--metabolite", dest="metabolite_id", help="Metabolite ID to verify")
    models_exists.add_argument("--gene", dest="gene_id", help="Gene ID to verify")

    models_export_ids = models_sub.add_parser(
        "export-ids", help="Export only IDs from model resource"
    )
    models_export_ids.add_argument("model_id", help="Model BiGG ID")
    models_export_ids.add_argument(
        "--type",
        dest="export_type",
        choices=("reactions", "metabolites", "genes"),
        required=True,
        help="Resource family to export IDs from",
    )

    models_stats = models_sub.add_parser("stats", help="Aggregate statistics over model catalog")
    models_stats.add_argument(
        "--organism", dest="organism_pattern", help="Filter by organism substring"
    )


def _add_universal_commands(subparsers: Any) -> None:
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

    where_reaction = universal_sub.add_parser(
        "where-reaction", help="List models containing a universal reaction"
    )
    where_reaction.add_argument("reaction_id", help="Reaction BiGG ID")

    where_metabolite = universal_sub.add_parser(
        "where-metabolite", help="List models containing a universal metabolite"
    )
    where_metabolite.add_argument("metabolite_id", help="Metabolite BiGG ID")


def _add_api_commands(subparsers: Any) -> None:
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

    fetch = subparsers.add_parser("fetch", help="Fetch path or URL with optional field extraction")
    fetch.add_argument("path_or_url", help="Absolute path or full URL")
    fetch.add_argument(
        "--query",
        action="append",
        default=[],
        metavar="KEY=VALUE",
        help="Query parameter, repeatable",
    )
    fetch.add_argument(
        "--field",
        action="append",
        default=[],
        metavar="PATH",
        help="Extract field path (supports dotted keys and [] for arrays)",
    )

    namespace = subparsers.add_parser("namespace", help="Download BiGG namespace resources")
    namespace_sub = namespace.add_subparsers(dest="namespace_command", required=True)

    ns_reactions = namespace_sub.add_parser("reactions", help="Download reactions namespace TSV")
    ns_reactions.add_argument(
        "--out", type=Path, help="Output path (default: bigg_models_reactions.txt)"
    )

    ns_metabolites = namespace_sub.add_parser(
        "metabolites", help="Download metabolites namespace TSV"
    )
    ns_metabolites.add_argument(
        "--out",
        type=Path,
        help="Output path (default: bigg_models_metabolites.txt)",
    )

    ns_universal_model = namespace_sub.add_parser(
        "universal-model", help="Download universal model JSON"
    )
    ns_universal_model.add_argument(
        "--out", type=Path, help="Output path (default: universal_model.json)"
    )


def build_parser() -> argparse.ArgumentParser:
    parser = _HelpParser(
        prog="bigg",
        description="Command-line interface for the BiGG Models API",
    )
    _add_common_global_flags(parser)
    subparsers = parser.add_subparsers(dest="command")
    subparsers.add_parser("version", help="Show BiGG database/API version")
    _add_search_commands(subparsers)
    _add_models_commands(subparsers)
    _add_universal_commands(subparsers)
    _add_api_commands(subparsers)
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
            return _print_rendered(
                op_search(
                    client,
                    query=args.query,
                    search_type=args.search_type,
                    limit=args.limit,
                ),
                output=output,
                context="search",
            )

        if command == "find":
            return _print_rendered(
                op_find(client, query=args.query, limit=args.limit),
                output=output,
                context="find",
            )

        if command == "show":
            return _print_rendered(
                op_show(client, identifier=args.identifier),
                output=output,
                context="show",
            )

        if command == "models":
            sub = args.models_command
            if sub == "list":
                return _print_rendered(
                    op_models_list(client, limit=args.limit), output=output, context="models.list"
                )
            if sub == "show":
                return _print_rendered(
                    op_models_show(client, model_id=args.model_id),
                    output=output,
                    context="models.show",
                )
            if sub == "summary":
                return _print_rendered(
                    op_models_summary(client, model_id=args.model_id),
                    output=output,
                    context="models.summary",
                )
            if sub == "download":
                model = op_models_download(client, model_id=args.model_id)
                out_path = args.out or Path(f"{args.model_id}.json")
                write_download(out_path, model)
                if output == "text":
                    print(f"Saved model JSON to {out_path}")
                return 0
            if sub == "download-static":
                payload = op_models_download_static(
                    client,
                    model_id=args.model_id,
                    fmt=args.static_format,
                )
                default_ext = args.static_format
                out_path = args.out or Path(f"{args.model_id}.{default_ext}")
                write_bytes(out_path, payload)
                if output == "text":
                    print(f"Saved static model file to {out_path}")
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
            if sub == "reaction-equation":
                return _print_rendered(
                    op_model_reaction_equation(
                        client,
                        model_id=args.model_id,
                        reaction_id=args.reaction_id,
                    ),
                    output=output,
                    context="models.reaction_equation",
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
                        client, model_id=args.model_id, metabolite_id=args.metabolite_id
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
            if sub == "exists":
                exists_data = op_models_exists(
                    client,
                    model_id=args.model_id,
                    reaction_id=args.reaction_id,
                    metabolite_id=args.metabolite_id,
                    gene_id=args.gene_id,
                )
                rendered = render_output(exists_data, output=output, context="models.exists")
                if rendered.content:
                    print(rendered.content)
                return 0 if bool(exists_data.get("exists", False)) else 1
            if sub == "export-ids":
                return _print_rendered(
                    op_model_export_ids(
                        client, model_id=args.model_id, export_type=args.export_type
                    ),
                    output=output,
                    context="models.export_ids",
                )
            if sub == "stats":
                return _print_rendered(
                    op_model_stats(client, organism_pattern=args.organism_pattern),
                    output=output,
                    context="models.stats",
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
            if sub == "where-reaction":
                return _print_rendered(
                    op_universal_where_reaction(client, reaction_id=args.reaction_id),
                    output=output,
                    context="universal.where_reaction",
                )
            if sub == "where-metabolite":
                return _print_rendered(
                    op_universal_where_metabolite(client, metabolite_id=args.metabolite_id),
                    output=output,
                    context="universal.where_metabolite",
                )

        if command == "api" and args.api_command == "get":
            return _print_rendered(
                op_api_get(client, path=args.path, query=args.query),
                output=output,
                context="api.get",
            )

        if command == "fetch":
            return _print_rendered(
                op_fetch(
                    client,
                    path_or_url=args.path_or_url,
                    query=args.query,
                    fields=args.field,
                ),
                output=output,
                context="fetch",
            )

        if command == "namespace":
            sub = args.namespace_command
            if sub == "reactions":
                payload = op_namespace_reactions(client)
                out_path = args.out or Path("bigg_models_reactions.txt")
                write_bytes(out_path, payload)
                if output == "text":
                    print(f"Saved namespace reactions to {out_path}")
                return 0
            if sub == "metabolites":
                payload = op_namespace_metabolites(client)
                out_path = args.out or Path("bigg_models_metabolites.txt")
                write_bytes(out_path, payload)
                if output == "text":
                    print(f"Saved namespace metabolites to {out_path}")
                return 0
            if sub == "universal-model":
                payload = op_namespace_universal_model(client)
                out_path = args.out or Path("universal_model.json")
                write_bytes(out_path, payload)
                if output == "text":
                    print(f"Saved universal model to {out_path}")
                return 0

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
        return int(exc.code) if isinstance(exc.code, int) else 0
    except (UsageError, ConfigError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2
    except (ApiError, BiggError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
