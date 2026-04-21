"""
Perfil de pesquisa (YAML): subreddits, palavras-chave, filtros e análise.

Carregado pelas Fases 1–3 para manter uma única fonte de verdade por estudo.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

_STUDY_ID_RE = re.compile(r"^[a-zA-Z0-9_]+$")

# Padrões originais de processor/cleaner.py (usados se o perfil omitir creator_patterns)
DEFAULT_CREATOR_PATTERNS: list[str] = [
    r"my video",
    r"my videos",
    r"my channel",
    r"meu canal",
    r"meus v[ií]deos",
    r"tested",
    r"tried",
    r"testei",
    r"experimentei",
    r"my followers",
    r"my niche",
]

# Regex padrão da Fase 3 (analise_corpus.py)
DEFAULT_TACTICS_PATTERN = (
    r"\b(tested|tried|experimented|changed my|adjusted|worked|didn[''`]?t work)\b"
)
DEFAULT_THEORIES_PATTERN = (
    r"(post \d+ times?|best time to post|retention rate|3 seconds?|watch time)"
)

DEFAULT_VOCABULARY = [
    "shadowban",
    "fyp",
    "algorithm",
    "retention",
    "engagement",
    "reach",
    "viral",
    "300 view jail",
    "metrics",
]


@dataclass
class StudySearch:
    time_filter: str = "year"
    max_posts_per_search: int = 40
    max_comments_per_post: int = 20
    delay_min: float = 2.0
    delay_max: float = 5.0
    headless_default: bool = True


@dataclass
class StudyFilters:
    min_comments: int = 3
    min_chars: int = 30
    creator_patterns: list[str] = field(default_factory=lambda: list(DEFAULT_CREATOR_PATTERNS))
    exclude_terms: list[str] = field(default_factory=list)
    require_any_terms: list[str] = field(default_factory=list)


@dataclass
class StudyAnalysis:
    report_title: str = "Relatório de análise do corpus"
    report_subtitle: str = "Corpus Reddit — Fase 3"
    vocabulary_terms: list[str] = field(default_factory=lambda: list(DEFAULT_VOCABULARY))
    tactics_pattern: str = DEFAULT_TACTICS_PATTERN
    theories_pattern: str = DEFAULT_THEORIES_PATTERN


@dataclass
class ResearchProfile:
    study_id: str
    theme_label: str
    subreddits: list[str]
    keyword_groups: dict[str, list[str]]
    search: StudySearch
    filters: StudyFilters
    analysis: StudyAnalysis

    def flattened_keywords(self) -> list[dict[str, str]]:
        return flatten_keywords(self.keyword_groups)


def compile_analysis_regex(pattern: str, field_name: str) -> re.Pattern[str]:
    """Compila regex da Fase 3; use a partir de StudyAnalysis.tactics_pattern / theories_pattern."""
    try:
        return re.compile(pattern, re.IGNORECASE)
    except re.error as exc:
        raise ValueError(f"Regex inválida em analysis.{field_name}: {exc}") from exc


def flatten_keywords(keyword_groups: dict[str, list[str]]) -> list[dict[str, str]]:
    return [
        {"group": group, "keyword": kw}
        for group, keywords in keyword_groups.items()
        for kw in keywords
    ]


def _require_str(d: dict[str, Any], key: str, path: str) -> str:
    v = d.get(key)
    if not isinstance(v, str) or not v.strip():
        raise ValueError(f"{path}: campo obrigatório '{key}' (string não vazia)")
    return v.strip()


def _require_list_str(d: dict[str, Any], key: str, path: str, min_len: int = 1) -> list[str]:
    v = d.get(key)
    if not isinstance(v, list) or len(v) < min_len:
        raise ValueError(f"{path}: '{key}' deve ser lista com pelo menos {min_len} item(ns)")
    out: list[str] = []
    for i, item in enumerate(v):
        if not isinstance(item, str) or not item.strip():
            raise ValueError(f"{path}.{key}[{i}]: string não vazia esperada")
        out.append(item.strip())
    return out


def _optional_list_str(d: dict[str, Any], key: str, default: list[str]) -> list[str]:
    v = d.get(key, default)
    if v is None:
        return list(default)
    if not isinstance(v, list):
        raise ValueError(f"'{key}' deve ser lista de strings ou vazio")
    out: list[str] = []
    for i, item in enumerate(v):
        if not isinstance(item, str):
            raise ValueError(f"'{key}[{i}]' deve ser string")
        s = item.strip()
        if s:
            out.append(s)
    return out


def _parse_keyword_groups(raw: Any, path: str) -> dict[str, list[str]]:
    if not isinstance(raw, dict) or not raw:
        raise ValueError(f"{path}: 'keyword_groups' deve ser um mapa não vazio")
    groups: dict[str, list[str]] = {}
    for name, kws in raw.items():
        if not isinstance(name, str) or not name.strip():
            raise ValueError(f"{path}.keyword_groups: nome de grupo inválido")
        if not isinstance(kws, list) or not kws:
            raise ValueError(f"{path}.keyword_groups['{name}']: lista não vazia esperada")
        cleaned: list[str] = []
        for j, kw in enumerate(kws):
            if not isinstance(kw, str) or not kw.strip():
                raise ValueError(f"{path}.keyword_groups['{name}'][{j}]: string não vazia")
            cleaned.append(kw.strip())
        groups[name.strip()] = cleaned
    return groups


def _parse_search(raw: Any) -> StudySearch:
    if raw is None:
        return StudySearch()
    if not isinstance(raw, dict):
        raise ValueError("'search' deve ser um mapa ou omitido")
    return StudySearch(
        time_filter=str(raw.get("time_filter", "year")).strip() or "year",
        max_posts_per_search=int(raw.get("max_posts_per_search", 40)),
        max_comments_per_post=int(raw.get("max_comments_per_post", 20)),
        delay_min=float(raw.get("delay_min", 2.0)),
        delay_max=float(raw.get("delay_max", 5.0)),
        headless_default=bool(raw.get("headless_default", True)),
    )


def _parse_filters(raw: Any) -> StudyFilters:
    if raw is None:
        return StudyFilters()
    if not isinstance(raw, dict):
        raise ValueError("'filters' deve ser um mapa ou omitido")
    creators = _optional_list_str(raw, "creator_patterns", list(DEFAULT_CREATOR_PATTERNS))
    if not creators:
        creators = list(DEFAULT_CREATOR_PATTERNS)
    return StudyFilters(
        min_comments=int(raw.get("min_comments", 3)),
        min_chars=int(raw.get("min_chars", 30)),
        creator_patterns=creators,
        exclude_terms=_optional_list_str(raw, "exclude_terms", []),
        require_any_terms=_optional_list_str(raw, "require_any_terms", []),
    )


def _parse_analysis(raw: Any) -> StudyAnalysis:
    if raw is None:
        return StudyAnalysis()
    if not isinstance(raw, dict):
        raise ValueError("'analysis' deve ser um mapa ou omitido")
    vocab = raw.get("vocabulary_terms")
    if vocab is None:
        vocab_list = list(DEFAULT_VOCABULARY)
    else:
        if not isinstance(vocab, list) or not vocab:
            raise ValueError("analysis.vocabulary_terms: lista não vazia ou omita para usar o padrão")
        vocab_list = []
        for i, t in enumerate(vocab):
            if not isinstance(t, str) or not t.strip():
                raise ValueError(f"analysis.vocabulary_terms[{i}]: string não vazia")
            vocab_list.append(t.strip())
    title = raw.get("report_title")
    if not isinstance(title, str) or not title.strip():
        title = "Relatório de análise do corpus"
    else:
        title = title.strip()
    subtitle = raw.get("report_subtitle", "Corpus Reddit — Fase 3")
    if not isinstance(subtitle, str):
        subtitle = "Corpus Reddit — Fase 3"
    else:
        subtitle = subtitle.strip() or "Corpus Reddit — Fase 3"
    tactics = raw.get("tactics_pattern", DEFAULT_TACTICS_PATTERN)
    theories = raw.get("theories_pattern", DEFAULT_THEORIES_PATTERN)
    if not isinstance(tactics, str) or not tactics.strip():
        tactics = DEFAULT_TACTICS_PATTERN
    if not isinstance(theories, str) or not theories.strip():
        theories = DEFAULT_THEORIES_PATTERN
    return StudyAnalysis(
        report_title=title,
        report_subtitle=subtitle,
        vocabulary_terms=vocab_list,
        tactics_pattern=tactics.strip(),
        theories_pattern=theories.strip(),
    )


def load_profile(path: str | Path) -> ResearchProfile:
    """
    Carrega e valida um perfil YAML.
    """
    p = Path(path)
    if not p.is_file():
        raise FileNotFoundError(f"Perfil não encontrado: {p}")

    with p.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        raise ValueError("Raiz do YAML deve ser um mapa")

    study_id = _require_str(data, "study_id", "raiz")
    if not _STUDY_ID_RE.match(study_id):
        raise ValueError(
            "study_id deve conter apenas letras, dígitos e underscore (ex.: meu_estudo_2026)"
        )

    theme_label = _require_str(data, "theme_label", "raiz")
    subreddits = _require_list_str(data, "subreddits", "raiz", min_len=1)
    keyword_groups = _parse_keyword_groups(data.get("keyword_groups"), "raiz")

    search = _parse_search(data.get("search"))
    filters = _parse_filters(data.get("filters"))
    analysis = _parse_analysis(data.get("analysis"))

    if search.max_posts_per_search < 1 or search.max_comments_per_post < 0:
        raise ValueError("search.max_posts_per_search >= 1 e max_comments_per_post >= 0")
    if search.delay_min < 0 or search.delay_max < search.delay_min:
        raise ValueError("search: delay_min/delay_max inválidos")

    compile_analysis_regex(analysis.tactics_pattern, "tactics_pattern")
    compile_analysis_regex(analysis.theories_pattern, "theories_pattern")

    return ResearchProfile(
        study_id=study_id,
        theme_label=theme_label,
        subreddits=subreddits,
        keyword_groups=keyword_groups,
        search=search,
        filters=filters,
        analysis=analysis,
    )
