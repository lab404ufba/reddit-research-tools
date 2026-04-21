"""
Lógica central de scraping do Reddit com Playwright.

Fluxo:
  1. Para cada (subreddit, keyword) → abre página de busca
  2. Scroll para carregar posts via infinite scroll
  3. Coleta URLs dos posts
  4. Para cada URL → extrai post + comentários e salva incrementalmente
"""

import logging
import random
import time
import urllib.parse
from urllib.parse import urlparse

from playwright.sync_api import BrowserContext, Page, TimeoutError as PWTimeout

from research_profile import ResearchProfile
from scraper.browser import new_page
from scraper.storage import JsonlStorage

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _sleep(delay_min: float, delay_max: float) -> None:
    delay = random.uniform(delay_min, delay_max)
    logger.debug("Aguardando %.1fs…", delay)
    time.sleep(delay)


def _build_search_url(subreddit: str, keyword: str, time_filter: str) -> str:
    q = urllib.parse.quote_plus(keyword)
    return (
        f"https://www.reddit.com/r/{subreddit}/search/"
        f"?q={q}&restrict_sr=1&t={time_filter}&sort=relevance"
    )


def _extract_post_id(url: str) -> str | None:
    """Extrai o ID do post a partir de URLs como /r/sub/comments/<id>/..."""
    parts = urlparse(url).path.strip("/").split("/")
    try:
        idx = parts.index("comments")
        return parts[idx + 1]
    except (ValueError, IndexError):
        return None


# ---------------------------------------------------------------------------
# Coleta de links (página de resultados de busca)
# ---------------------------------------------------------------------------

def collect_post_links(
    page: Page,
    subreddit: str,
    keyword: str,
    *,
    time_filter: str,
    max_posts: int,
    delay_min: float,
    delay_max: float,
) -> list[str]:
    """
    Acessa a página de busca, faz scroll para carregar posts
    e retorna até `max_posts` URLs únicas de posts.
    """
    url = _build_search_url(subreddit, keyword, time_filter)
    logger.info("[BUSCA] r/%s | '%s' → %s", subreddit, keyword, url)

    try:
        page.goto(url, wait_until="domcontentloaded")
    except PWTimeout:
        logger.warning("Timeout ao carregar página de busca: %s", url)
        return []

    _sleep(delay_min, delay_max)

    links: list[str] = []
    max_scrolls = 8
    scroll_pause = 2.0

    for scroll_n in range(max_scrolls):
        # Coleta links de posts visíveis
        anchors = page.query_selector_all('a[href*="/comments/"]')
        for a in anchors:
            href = a.get_attribute("href") or ""
            # Normaliza para URL absoluta
            if href.startswith("/"):
                href = "https://www.reddit.com" + href
            # Filtra apenas páginas de post do subreddit correto
            if f"/r/{subreddit}/comments/" in href:
                # Remove query string e fragmento
                clean = href.split("?")[0].rstrip("/")
                if clean not in links:
                    links.append(clean)

        logger.debug(
            "Scroll %d/%d — links acumulados: %d", scroll_n + 1, max_scrolls, len(links)
        )

        if len(links) >= max_posts:
            break

        # Scroll até o final da página
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        time.sleep(scroll_pause)

    return links[:max_posts]


# ---------------------------------------------------------------------------
# Extração profunda de um post individual
# ---------------------------------------------------------------------------

def extract_post_data(
    page: Page,
    post_url: str,
    subreddit: str,
    keyword_info: dict,
    *,
    study_id: str,
    theme_label: str,
    max_comments_per_post: int,
    delay_min: float,
    delay_max: float,
) -> dict | None:
    """
    Acessa a página de um post e extrai metadados + comentários.
    Retorna None se a extração falhar.
    """
    logger.info("[POST] %s", post_url)
    try:
        page.goto(post_url, wait_until="domcontentloaded")
    except PWTimeout:
        logger.warning("Timeout ao carregar post: %s", post_url)
        return None

    _sleep(delay_min, delay_max)

    try:
        post_data = _parse_post(
            page,
            post_url,
            subreddit,
            keyword_info,
            study_id=study_id,
            theme_label=theme_label,
        )
        comments = _parse_comments(page, max_comments_per_post=max_comments_per_post)
    except Exception as exc:
        logger.error("Erro ao parsear %s: %s", post_url, exc, exc_info=True)
        return None

    return {"post": post_data, "comments": comments}


def _parse_post(
    page: Page,
    url: str,
    subreddit: str,
    keyword_info: dict,
    *,
    study_id: str,
    theme_label: str,
) -> dict:
    """Extrai metadados do post original."""
    post_id = _extract_post_id(url) or ""

    # Título
    title = _safe_text(page, 'h1[slot="title"], h1, [data-testid="post-title"]')

    # Autor
    author = _safe_attr(
        page,
        'a[href*="/user/"], [data-testid="post_author_link"]',
        "href",
    )
    if author:
        author = author.strip("/").split("/")[-1]

    # Corpo do texto (pode não existir em posts de link/imagem)
    body = _safe_text(
        page,
        '[data-testid="post-rtjson-content"], .RichTextJSON-root, '
        '[slot="text-body"] p',
    )

    # Upvotes
    upvotes_raw = _safe_text(
        page,
        'faceplate-number[pretty=""], [id*="vote-count"], '
        '[data-testid="vote-arrows"] faceplate-number',
    )
    upvotes = _parse_int(upvotes_raw)

    # Número de comentários
    comment_count_raw = _safe_text(
        page,
        'a[href$="/#newcomments"] faceplate-number, '
        '[data-testid="comment-count"], '
        'a:-soup-contains("comments") faceplate-number',
    )
    comment_count = _parse_int(comment_count_raw)

    # Timestamp
    timestamp = _safe_attr(page, "time[datetime]", "datetime")

    return {
        "id": post_id,
        "subreddit": subreddit,
        "keyword_group": keyword_info.get("group", ""),
        "keyword": keyword_info.get("keyword", ""),
        "study_id": study_id,
        "theme_label": theme_label,
        "url": url,
        "title": title,
        "author": author,
        "body": body,
        "upvotes": upvotes,
        "comment_count": comment_count,
        "timestamp": timestamp,
    }


def _parse_comments(page: Page, *, max_comments_per_post: int) -> list[dict]:
    """Extrai os top comentários do post."""
    comments: list[dict] = []

    # Seletores para threads de comentários no Reddit (old e new design)
    comment_selectors = [
        "shreddit-comment",          # New Reddit (web components)
        ".Comment",                  # Old/alternative layout
        '[data-testid="comment"]',
    ]

    for selector in comment_selectors:
        elements = page.query_selector_all(selector)
        if elements:
            for el in elements[:max_comments_per_post]:
                try:
                    author_el = el.query_selector(
                        'a[href*="/user/"], [slot="authorName"]'
                    )
                    author = (author_el.inner_text().strip() if author_el else "")

                    body_el = el.query_selector(
                        '[slot="comment"] p, .RichTextJSON-root p, .md p'
                    )
                    body = (body_el.inner_text().strip() if body_el else "")

                    score_el = el.query_selector(
                        "faceplate-number, .score, [data-testid='comment-score']"
                    )
                    score_raw = score_el.inner_text().strip() if score_el else "0"
                    score = _parse_int(score_raw)

                    if author or body:
                        comments.append(
                            {"author": author, "body": body, "upvotes": score}
                        )
                except Exception as exc:
                    logger.debug("Erro ao extrair comentário: %s", exc)
            break  # Para no primeiro seletor que retornou resultados

    return comments


# ---------------------------------------------------------------------------
# Utilitários de seleção
# ---------------------------------------------------------------------------

def _safe_text(page: Page, selector: str) -> str:
    try:
        el = page.query_selector(selector)
        return el.inner_text().strip() if el else ""
    except Exception:
        return ""


def _safe_attr(page: Page, selector: str, attr: str) -> str:
    try:
        el = page.query_selector(selector)
        val = el.get_attribute(attr) if el else None
        return (val or "").strip()
    except Exception:
        return ""


def _parse_int(raw: str) -> int:
    """Converte strings como '1.2k', '823' para int."""
    if not raw:
        return 0
    raw = raw.strip().lower().replace(",", "")
    try:
        if raw.endswith("k"):
            return int(float(raw[:-1]) * 1_000)
        if raw.endswith("m"):
            return int(float(raw[:-1]) * 1_000_000)
        return int(float(raw))
    except (ValueError, TypeError):
        return 0


# ---------------------------------------------------------------------------
# Loop principal
# ---------------------------------------------------------------------------

def run_scraper(context: BrowserContext, storage: JsonlStorage, profile: ResearchProfile) -> None:
    """
    Itera sobre todas as combinações (subreddit × keyword),
    coleta links e extrai dados de cada post.
    """
    total_saved = 0
    total_skipped = 0
    s = profile.search
    keywords = profile.flattened_keywords()

    for subreddit in profile.subreddits:
        for kw_info in keywords:
            search_page = new_page(context)
            try:
                post_links = collect_post_links(
                    search_page,
                    subreddit,
                    kw_info["keyword"],
                    time_filter=s.time_filter,
                    max_posts=s.max_posts_per_search,
                    delay_min=s.delay_min,
                    delay_max=s.delay_max,
                )
            finally:
                search_page.close()

            logger.info(
                "  → %d links coletados para r/%s | '%s'",
                len(post_links),
                subreddit,
                kw_info["keyword"],
            )

            for link in post_links:
                post_id = _extract_post_id(link)
                if post_id and storage.is_seen(post_id):
                    logger.debug("Post já coletado, pulando: %s", post_id)
                    total_skipped += 1
                    continue

                post_page = new_page(context)
                try:
                    record = extract_post_data(
                        post_page,
                        link,
                        subreddit,
                        kw_info,
                        study_id=profile.study_id,
                        theme_label=profile.theme_label,
                        max_comments_per_post=s.max_comments_per_post,
                        delay_min=s.delay_min,
                        delay_max=s.delay_max,
                    )
                    if record:
                        storage.save(record)
                        total_saved += 1
                        logger.info(
                            "  [OK] Salvo #%d — '%s'",
                            total_saved,
                            record["post"].get("title", "")[:60],
                        )
                except Exception as exc:
                    logger.error("Falha inesperada no post %s: %s", link, exc, exc_info=True)
                finally:
                    post_page.close()

                _sleep(s.delay_min, s.delay_max)

    logger.info(
        "Coleta finalizada. Salvos: %d | Pulados (duplicatas): %d",
        total_saved,
        total_skipped,
    )
