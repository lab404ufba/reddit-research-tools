"""
Entry point da Fase 1 — Coleta bruta do Reddit.

Uso:
    python main.py
    python main.py --profile profiles/examples/minimo.yaml
    python main.py --no-headless
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

import paths
from research_profile import load_profile
from scraper.browser import create_browser
from scraper.reddit_scraper import run_scraper
from scraper.storage import JsonlStorage


def setup_logging(log_file: Path) -> None:
    log_file.parent.mkdir(parents=True, exist_ok=True)
    fmt = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    logging.basicConfig(
        level=logging.INFO,
        format=fmt,
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(log_file, encoding="utf-8"),
        ],
        force=True,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fase 1 — Coleta bruta de posts do Reddit (perfil YAML)."
    )
    parser.add_argument(
        "--profile",
        type=str,
        default=str(paths.DEFAULT_PROFILE_PATH),
        help="Caminho do perfil de pesquisa (.yaml). Padrão: exemplo fofoca algorítmica.",
    )
    parser.add_argument(
        "--no-headless",
        action="store_true",
        help="Abre o browser visualmente (útil para debug).",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    profile_path = Path(args.profile)
    profile = load_profile(profile_path)
    study_paths = paths.paths_for_study(profile.study_id)

    setup_logging(study_paths.scraper_log)

    logger = logging.getLogger("main")
    if profile_path.resolve() == paths.DEFAULT_PROFILE_PATH.resolve():
        logger.info("Usando perfil padrão (exemplo reprodutível): %s", profile_path)

    headless = False if args.no_headless else profile.search.headless_default

    logger.info("=" * 60)
    logger.info("Iniciando Fase 1 — Reddit Raw Scraper")
    logger.info("Estudo: %s — %s", profile.study_id, profile.theme_label)
    logger.info("Saída: %s", study_paths.raw_jsonl)
    logger.info("Subreddits: %s", profile.subreddits)
    logger.info("Keywords: %d total", len(profile.flattened_keywords()))
    logger.info("Log: %s", study_paths.scraper_log)
    logger.info("=" * 60)

    storage = JsonlStorage(str(study_paths.raw_jsonl))

    with create_browser(headless=headless) as (_, context):
        run_scraper(context, storage, profile)

    logger.info("Fase 1 concluída. Arquivo: %s", study_paths.raw_jsonl)


if __name__ == "__main__":
    main()
