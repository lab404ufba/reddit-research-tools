"""
Análise do Corpus — Fase 3 (relatório Markdown parametrizado pelo perfil YAML).

Lê o Excel da Fase 2, imprime o relatório no console e salva em reports/.

Uso:
    python analise_corpus.py
    python analise_corpus.py --profile profiles/examples/minimo.yaml
    python analise_corpus.py --input data/processed/meu_estudo_corpus.xlsx --profile ...
"""

from __future__ import annotations

import argparse
import re
from collections import Counter
from datetime import datetime
from pathlib import Path

import pandas as pd

import paths
from research_profile import ResearchProfile, compile_analysis_regex, load_profile


def _vocabulario_patterns(terms: list[str]) -> dict[str, re.Pattern[str]]:
    return {
        term: re.compile(re.escape(term), re.IGNORECASE)
        for term in terms
    }


def load_data(filepath: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    xl = pd.read_excel(filepath, sheet_name=None, engine="openpyxl")
    df_posts = xl["Posts"].fillna("")
    df_comments = xl["Comentarios"].fillna("")
    return df_posts, df_comments


def _count_term(pattern: re.Pattern[str], series: pd.Series) -> int:
    return series.apply(lambda t: len(pattern.findall(str(t)))).sum()


def map_vocabulario(
    df_posts: pd.DataFrame,
    df_comments: pd.DataFrame,
    vocab_patterns: dict[str, re.Pattern[str]],
) -> Counter:
    """Conta frequência de cada termo configurado em posts + comentários."""
    post_text = (df_posts["Titulo"].astype(str) + " " + df_posts["Texto"].astype(str))
    comment_text = df_comments["Texto_Comentario"].astype(str)

    counts: Counter = Counter()
    for term, pattern in vocab_patterns.items():
        counts[term] = _count_term(pattern, post_text) + _count_term(pattern, comment_text)
    return counts


def map_taticas(
    df_posts: pd.DataFrame,
    df_comments: pd.DataFrame,
    tactics_pattern: re.Pattern[str],
) -> dict:
    """Conta posts e comentários que casam com a regex de táticas."""
    post_text = df_posts["Titulo"].astype(str) + " " + df_posts["Texto"].astype(str)
    posts_com_tatica = post_text.apply(
        lambda t: bool(tactics_pattern.search(t))
    ).sum()
    comments_com_tatica = df_comments["Texto_Comentario"].apply(
        lambda t: bool(tactics_pattern.search(str(t)))
    ).sum()
    return {"posts": int(posts_com_tatica), "comentarios": int(comments_com_tatica)}


def map_teorias(
    df_posts: pd.DataFrame,
    df_comments: pd.DataFrame,
    theories_pattern: re.Pattern[str],
) -> dict:
    """Conta posts e comentários que casam com a regex de teorias/regras."""
    post_text = df_posts["Titulo"].astype(str) + " " + df_posts["Texto"].astype(str)
    posts_com_teoria = post_text.apply(
        lambda t: bool(theories_pattern.search(t))
    ).sum()
    comments_com_teoria = df_comments["Texto_Comentario"].apply(
        lambda t: bool(theories_pattern.search(str(t)))
    ).sum()
    return {"posts": int(posts_com_teoria), "comentarios": int(comments_com_teoria)}


def build_report(df_posts: pd.DataFrame, df_comments: pd.DataFrame, profile: ResearchProfile) -> str:
    """
    Constrói o relatório completo como uma string Markdown.
    """
    analysis = profile.analysis
    vocab_patterns = _vocabulario_patterns(analysis.vocabulary_terms)
    tactics_re = compile_analysis_regex(analysis.tactics_pattern, "tactics_pattern")
    theories_re = compile_analysis_regex(analysis.theories_pattern, "theories_pattern")

    lines: list[str] = []
    L = lines.append

    generated_at = datetime.now().strftime("%d/%m/%Y %H:%M")

    L(f"# {analysis.report_title}")
    L("")
    L(f"> **{analysis.report_subtitle}**")
    L(f"> Gerado em: {generated_at}")
    L("")
    L("---")

    L("")
    L("## 1. Estatísticas Gerais")
    L("")
    L("| Métrica | Valor |")
    L("|---|---:|")
    L(f"| Total de posts | **{len(df_posts)}** |")
    L(f"| Total de comentários | **{len(df_comments)}** |")
    L("")
    L("### Distribuição por Subreddit")
    L("")
    L("| Subreddit | Posts | Barra |")
    L("|---|---:|---|")
    dist = (
        df_posts["Subreddit"]
        .value_counts()
        .reset_index()
        .rename(columns={"count": "Posts"})
    )
    max_posts = max(dist["Posts"]) if len(dist) else 1
    for _, row in dist.iterrows():
        bar = "█" * min(int(row["Posts"] / max_posts * 20), 20)
        L(f"| r/{row['Subreddit']} | {row['Posts']} | `{bar}` |")

    L("")
    L("---")

    L("")
    L("## 2. Posts de Criadores (`is_creator_suspect`)")
    L("")
    n_suspect = int(df_posts["is_creator_suspect"].astype(str).str.lower().eq("true").sum())
    pct = n_suspect / len(df_posts) * 100 if len(df_posts) else 0
    L(f"- Posts marcados como **criador suspeito**: **{n_suspect}** ({pct:.1f}% do total)")
    L(f"- Posts de outros usuários: {len(df_posts) - n_suspect}")
    L("")
    L("---")

    L("")
    L("## 3. Vocabulário monitorado")
    L("")
    L("Frequência dos termos configurados no perfil (posts **e** comentários).")
    L("")
    L("| # | Termo | Ocorrências |")
    L("|---:|---|---:|")
    vocab_counts = map_vocabulario(df_posts, df_comments, vocab_patterns)
    for rank, (term, count) in enumerate(vocab_counts.most_common(10), start=1):
        L(f"| {rank} | `{term}` | {count} |")
    L("")
    L("---")

    L("")
    L("## 4. Táticas e experimentações (regex do perfil)")
    L("")
    L("Padrões definidos em `analysis.tactics_pattern` e `analysis.theories_pattern`.")
    L("")
    taticas = map_taticas(df_posts, df_comments, tactics_re)
    L("| Contexto | Contagem |")
    L("|---|---:|")
    L(f"| Posts com match em táticas | {taticas['posts']} |")
    L(f"| Comentários com match em táticas | {taticas['comentarios']} |")
    L("")
    teorias = map_teorias(df_posts, df_comments, theories_re)
    L("| Contexto | Contagem |")
    L("|---|---:|")
    L(f"| Posts com match em teorias/regras | {teorias['posts']} |")
    L(f"| Comentários com match em teorias/regras | {teorias['comentarios']} |")
    L("")
    L("---")

    L("")
    L("## 5. Ranking de discussão — Top 5 (prioridade para codificação)")
    L("")
    L("Posts com maior número de comentários — candidatos prioritários para codificação manual.")
    L("")
    top5 = df_posts.sort_values("Num_Comentarios", ascending=False).head(5)
    for rank, (_, row) in enumerate(top5.iterrows(), start=1):
        is_creator = str(row.get("is_creator_suspect", "")).lower() == "true"
        creator_badge = " `★ CRIADOR`" if is_creator else ""
        titulo = str(row["Titulo"])[:100]
        L(f"### #{rank} — r/{row['Subreddit']}{creator_badge}")
        L("")
        L(f"**Título:** {titulo}")
        L("")
        L("| Comentários | Upvotes |")
        L("|---:|---:|")
        L(f"| {row['Num_Comentarios']} | {row['Upvotes']} |")
        L("")
        L(f"**URL:** <{row['URL']}>")
        L("")

    L("---")
    L("")
    L(f"*Relatório gerado automaticamente em {generated_at}.*")
    L("")

    return "\n".join(lines)


def save_report(content: str, study_id: str) -> Path:
    """Salva o relatório em reports/ com timestamp e study_id no nome."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    filename = paths.paths_for_study(study_id).reports_dir / f"relatorio_{study_id}_{timestamp}.md"
    filename.write_text(content, encoding="utf-8")
    return filename


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fase 3 — Análise exploratória do corpus Reddit (perfil YAML)."
    )
    parser.add_argument(
        "--profile",
        type=str,
        default=str(paths.DEFAULT_PROFILE_PATH),
        help="Perfil com títulos, vocabulário e regexes da Fase 3.",
    )
    parser.add_argument(
        "--input",
        default=None,
        help="Excel da Fase 2. Padrão: data/processed/<study_id>_corpus.xlsx do perfil.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    profile = load_profile(Path(args.profile))
    study_paths = paths.paths_for_study(profile.study_id)
    input_path = args.input or str(study_paths.corpus_xlsx)

    df_posts, df_comments = load_data(input_path)
    report = build_report(df_posts, df_comments, profile)
    print(report)
    saved_to = save_report(report, profile.study_id)
    print(f"Relatorio salvo em: {saved_to.resolve()}")


if __name__ == "__main__":
    main()
