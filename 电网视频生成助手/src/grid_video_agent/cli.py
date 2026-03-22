from __future__ import annotations

import argparse
from pathlib import Path

from .config import load_agent_config
from .fetchers import fetch_latest_grid_items
from .pipeline import run_pipeline, run_pipeline_from_items
from .video_renderer import render_preview_bundle


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate grid short-video assets from local data or live web sources.")
    parser.add_argument("--input", help="Path to an input JSON/JSONL/CSV file or directory.")
    parser.add_argument("--output", required=True, help="Directory to write generated assets.")
    parser.add_argument(
        "--mode",
        choices=["rule", "auto", "api"],
        default=None,
        help="Generation mode. rule uses local heuristics, auto/api attempts model generation.",
    )
    parser.add_argument(
        "--fetch-web",
        action="store_true",
        help="Fetch grid news from configured web sources. If --input is omitted, web fetching is used automatically.",
    )
    parser.add_argument(
        "--source-set",
        choices=["official", "mixed"],
        default=None,
        help="Which built-in source registry to use when fetching from the web.",
    )
    parser.add_argument("--per-source-limit", type=int, default=None, help="Maximum articles to keep per source.")
    parser.add_argument("--total-fetch-limit", type=int, default=None, help="Maximum total fetched items.")
    parser.add_argument(
        "--render-preview",
        action="store_true",
        help="Render storyboard PNG frames plus an animated GIF preview from the generated script.",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    output_dir = Path(args.output)
    config = load_agent_config()
    if args.mode:
        config.model_mode = args.mode
    if args.source_set:
        config.source_set = args.source_set
    if args.per_source_limit:
        config.per_source_limit = args.per_source_limit
    if args.total_fetch_limit:
        config.total_fetch_limit = args.total_fetch_limit

    use_web = args.fetch_web or not args.input
    if use_web:
        items, notes = fetch_latest_grid_items(
            config=config,
            output_dir=output_dir,
            source_set=args.source_set,
            per_source_limit=args.per_source_limit,
            total_limit=args.total_fetch_limit,
        )
        plan, _ = run_pipeline_from_items(items, output_dir, config, input_mode="web", warnings=notes)
    else:
        plan, _ = run_pipeline(Path(args.input), output_dir, config)

    if args.render_preview:
        render_preview_bundle(plan, output_dir)


if __name__ == "__main__":
    main()
