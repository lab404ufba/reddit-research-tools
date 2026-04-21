"""
Filtros metodológicos da Fase 2.

Aplica o funil de limpeza e retorna dois DataFrames relacionais:
  - df_posts      : um post por linha
  - df_comentarios: um comentário por linha (chave estrangeira Post_ID)
"""

import re

import pandas as pd

from research_profile import StudyFilters


def _creator_regex(patterns: list[str]) -> re.Pattern[str]:
    return re.compile("|".join(patterns), flags=re.IGNORECASE)


def _text_lower(title: str, body: str) -> str:
    return f"{title} {body}".lower()


def apply_filters(df: pd.DataFrame, filt: StudyFilters) -> pd.DataFrame:
    """Aplica o funil de limpeza e retorna o DataFrame de posts filtrado."""
    creator_re = _creator_regex(filt.creator_patterns)

    # ── Pré-processamento ──────────────────────────────────────────────────

    df = df.copy()
    df["qtd_comentarios_reais"] = df["comments"].apply(len)

    df["title"] = df["title"].fillna("").astype(str)
    df["body"] = df["body"].fillna("").astype(str)

    # ── Deduplicação ───────────────────────────────────────────────────────
    before = len(df)
    df = df.drop_duplicates(subset="id", keep="first")
    after_dedup = len(df)
    print(f"  [DEDUP]   Após remover duplicatas         : {after_dedup:>6}  "
          f"(-{before - after_dedup})")

    # ── Regra 1: Discussão Coletiva ────────────────────────────────────────
    df = df[df["qtd_comentarios_reais"] >= filt.min_comments]
    after_r1 = len(df)
    print(f"  [REGRA 1] >= {filt.min_comments} comentários reais           : {after_r1:>6}  "
          f"(-{after_dedup - after_r1})")

    # ── Regra 2: Relevância — is_creator_suspect ───────────────────────────
    df["is_creator_suspect"] = (
        df["title"].str.contains(creator_re, regex=True)
        | df["body"].str.contains(creator_re, regex=True)
    )
    suspects = df["is_creator_suspect"].sum()
    print(f"  [REGRA 2] is_creator_suspect = True       : {suspects:>6}  (coluna adicionada, sem descarte)")

    # ── Regra 3: Tamanho mínimo ────────────────────────────────────────────
    df["_content_len"] = df["title"].str.len() + df["body"].str.len()
    df = df[df["_content_len"] >= filt.min_chars]
    df = df.drop(columns=["_content_len"])
    after_r3 = len(df)
    print(f"  [REGRA 3] título+body >= {filt.min_chars} chars         : {after_r3:>6}  "
          f"(-{after_r1 - after_r3})")

    # ── Exclusão por termos (substring, case-insensitive) ───────────────────
    if filt.exclude_terms:
        def _has_exclude(row: pd.Series) -> bool:
            blob = _text_lower(str(row["title"]), str(row["body"]))
            return any(term.lower() in blob for term in filt.exclude_terms)

        mask_ex = df.apply(_has_exclude, axis=1)
        dropped_ex = int(mask_ex.sum())
        df = df[~mask_ex]
        after_ex = len(df)
        print(f"  [EXCLUIR] termos em exclude_terms        : {after_ex:>6}  "
              f"(-{dropped_ex})")
    else:
        after_ex = after_r3

    # ── Inclusão: pelo menos um termo em require_any_terms ─────────────────
    if filt.require_any_terms:
        def _has_require(row: pd.Series) -> bool:
            blob = _text_lower(str(row["title"]), str(row["body"]))
            return any(term.lower() in blob for term in filt.require_any_terms)

        mask_req = df.apply(_has_require, axis=1)
        dropped_req = int((~mask_req).sum())
        df = df[mask_req]
        after_req = len(df)
        print(f"  [INCLUIR] require_any_terms (≥1 match)   : {after_req:>6}  "
              f"(-{dropped_req})")
    else:
        after_req = after_ex

    print(f"  {'─'*45}")
    print(f"  [SAÍDA]   Posts aprovados no funil        : {after_req:>6}")

    return df


def build_dataframes(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Constrói df_posts e df_comentarios a partir do DataFrame filtrado.
    """
    df_posts = df[[
        "id", "subreddit", "keyword", "title", "author",
        "body", "upvotes", "qtd_comentarios_reais", "timestamp",
        "url", "is_creator_suspect",
        "study_id", "theme_label",
    ]].copy()

    df_posts.columns = [
        "ID", "Subreddit", "Keyword", "Titulo", "Autor",
        "Texto", "Upvotes", "Num_Comentarios", "Data",
        "URL", "is_creator_suspect",
        "Study_ID", "Theme",
    ]

    rows: list[dict] = []
    for _, row in df.iterrows():
        post_id = row["id"]
        for comment in row["comments"]:
            rows.append({
                "Post_ID": post_id,
                "Autor_Comentario": comment.get("author", ""),
                "Texto_Comentario": comment.get("body", ""),
                "Upvotes_Comentario": comment.get("upvotes", 0),
            })

    df_comentarios = pd.DataFrame(
        rows,
        columns=["Post_ID", "Autor_Comentario", "Texto_Comentario", "Upvotes_Comentario"],
    )

    print(f"\n  Linhas em df_posts        : {len(df_posts)}")
    print(f"  Linhas em df_comentarios  : {len(df_comentarios)}")

    return df_posts, df_comentarios
