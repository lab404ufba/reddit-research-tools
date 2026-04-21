"""
Entry point da limpeza e exportação.

Uso:
    python process.py
    python process.py --profile profiles/examples/minimo.yaml
    python process.py --input data/raw/estudo_raw.jsonl --output data/processed/estudo_corpus.xlsx
"""

from __future__ import annotations

import argparse
from pathlib import Path

import paths
from research_profile import load_profile
from processor.loader import load_jsonl
from processor.cleaner import apply_filters, build_dataframes
from processor.exporter import export_to_excel


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fase 2 — Limpeza e exportação do corpus Reddit (perfil YAML)."
    )
    parser.add_argument(
        "--profile",
        type=str,
        default=str(paths.DEFAULT_PROFILE_PATH),
        help="Perfil com filtros (min_comments, exclude_terms, …).",
    )
    parser.add_argument(
        "--input",
        default=None,
        help="JSONL da Fase 1. Padrão: data/raw/<study_id>_raw.jsonl do perfil.",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Excel de saída. Padrão: data/processed/<study_id>_corpus.xlsx do perfil.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    profile = load_profile(Path(args.profile))
    study_paths = paths.paths_for_study(profile.study_id)

    input_path = args.input or str(study_paths.raw_jsonl)
    output_path = args.output or str(study_paths.corpus_xlsx)

    df_raw = load_jsonl(input_path)
    df_filtered = apply_filters(df_raw, profile.filters)
    df_posts, df_comentarios = build_dataframes(df_filtered)
    export_to_excel(df_posts, df_comentarios, output_path)


if __name__ == "__main__":
    main()
