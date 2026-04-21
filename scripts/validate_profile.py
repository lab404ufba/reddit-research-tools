#!/usr/bin/env python3
"""
Valida um perfil YAML com a mesma lógica que main.py / process.py / analise_corpus.py.

Uso:
    python scripts/validate_profile.py
    python scripts/validate_profile.py profiles/examples/meu_estudo.yaml
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import paths  # noqa: E402
from research_profile import load_profile  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Valida perfil YAML (sem browser nem rede)."
    )
    parser.add_argument(
        "profile",
        nargs="?",
        type=Path,
        default=paths.DEFAULT_PROFILE_PATH,
        help="Caminho do .yaml (default: perfil exemplo fofoca algorítmica).",
    )
    args = parser.parse_args()

    profile = load_profile(args.profile.resolve())
    sp = paths.paths_for_study(profile.study_id)
    n_kw = len(profile.flattened_keywords())

    print("Perfil OK.")
    print(f"  study_id       : {profile.study_id}")
    print(f"  theme_label    : {profile.theme_label}")
    print(f"  subreddits     : {len(profile.subreddits)}")
    print(f"  keyword_groups : {len(profile.keyword_groups)} → {n_kw} buscas")
    print(f"  raw JSONL      : {sp.raw_jsonl}")
    print(f"  corpus XLSX    : {sp.corpus_xlsx}")
    print(f"  scraper log    : {sp.scraper_log}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (FileNotFoundError, ValueError) as exc:
        print(f"Erro: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
