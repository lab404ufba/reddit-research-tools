"""
Caminhos canônicos do projeto.

Importar este módulo garante que todos os diretórios de saída
existam antes de qualquer leitura ou escrita de arquivo.

Arquivos por estudo usam `paths_for_study(study_id)` (ver `research_profile.load_profile`).
"""

from dataclasses import dataclass
from pathlib import Path

# Raiz do projeto (onde este arquivo está)
ROOT = Path(__file__).parent

# Diretórios
DATA_RAW = ROOT / "data" / "raw"
DATA_PROCESSED = ROOT / "data" / "processed"
LOGS = ROOT / "logs"
REPORTS = ROOT / "reports"

# Cria todos os diretórios ao importar (idempotente)
for _dir in (DATA_RAW, DATA_PROCESSED, LOGS, REPORTS):
    _dir.mkdir(parents=True, exist_ok=True)

# Perfil YAML padrão (estudo reprodutível original)
DEFAULT_PROFILE_PATH = ROOT / "profiles" / "examples" / "fofoca_algoritmica.yaml"


@dataclass(frozen=True)
class StudyPaths:
    """Caminhos de saída derivados do `study_id` do perfil."""

    study_id: str
    raw_jsonl: Path
    corpus_xlsx: Path
    scraper_log: Path
    reports_dir: Path


def paths_for_study(study_id: str) -> StudyPaths:
    """JSONL bruto, Excel processado e log do scraper por identificador de estudo."""
    sid = study_id.strip()
    return StudyPaths(
        study_id=sid,
        raw_jsonl=DATA_RAW / f"{sid}_raw.jsonl",
        corpus_xlsx=DATA_PROCESSED / f"{sid}_corpus.xlsx",
        scraper_log=LOGS / f"scraper_{sid}.log",
        reports_dir=REPORTS,
    )
