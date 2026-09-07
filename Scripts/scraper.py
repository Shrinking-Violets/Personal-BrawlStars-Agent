"""
Scraper for the Brawl Stars blog / release-notes archive on supercell.com.

Site: https://supercell.com/en/games/brawlstars/blog/

Notes on the site structure (as of Aug 2026):
- It's a Next.js site, but pages are server-rendered, so `requests` + BeautifulSoup
  is enough — no need for Selenium/Playwright.
- The listing page shows article "cards" (image, "Blog – Brawl Stars" label, date,
  title link) and is paginated at /blog/page/2/, /blog/page/3/, etc.
- CSS classes on this site are hashed CSS-module names (e.g.
  "archivedArticles_list__5wxZz") that can change on every deploy. Relying on the
  exact hash is brittle, so this scraper:
    1. Tries a partial/prefix class match first (class*="archivedArticles_list"),
    2. Falls back to a structural heuristic (any <a> whose href looks like a blog
       post permalink) if the class-based lookup finds nothing.
- Individual article pages (e.g. a "Release Notes ..." post) don't have a single
  reliably-named "article body" div either, so the body is extracted by taking
  everything between the H1/H2 post title and the site footer/nav.

Usage:
    python scrape_brawlstars_blog.py                      # scrape all release notes
    python scrape_brawlstars_blog.py --max-pages 3         # limit listing pages
    python scrape_brawlstars_blog.py --category release-notes --all-fields
"""

from __future__ import annotations

import argparse
import json
import re
import time
from dataclasses import dataclass, field
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from bs4.element import Tag
from langchain_core.documents import Document

BASE_URL = "https://supercell.com"
BLOG_URL = "https://supercell.com/en/games/brawlstars/blog/"

HEADERS = {
    # A normal browser UA avoids some basic bot-blocking.
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

# Matches dates like "3 Aug 2026" that appear next to each article card.
DATE_RE = re.compile(r"\b\d{1,2}\s+[A-Z][a-z]{2}\s+\d{4}\b")

# A blog post permalink looks like /en/games/brawlstars/blog/<category>/<slug>/
POST_HREF_RE = re.compile(r"/en/games/brawlstars/blog/[^/]+/[^/]+/?$")


@dataclass
class ArticleMeta:
    title: str
    url: str
    date: str | None
    category: str | None  # derived from the URL path, e.g. "release-notes"


def _get_soup(session: requests.Session, url: str) -> BeautifulSoup:
    resp = session.get(url, headers=HEADERS, timeout=20)
    resp.raise_for_status()
    return BeautifulSoup(resp.text, "html.parser")


def _category_from_url(url: str) -> str | None:
    path = urlparse(url).path.strip("/").split("/")
    # .../blog/<category>/<slug>
    if "blog" in path:
        idx = path.index("blog")
        if len(path) > idx + 1:
            return path[idx + 1]
    return None


def _extract_cards_by_class(soup: BeautifulSoup) -> list[Tag]:
    """Primary strategy: find the archive container by a partial class match."""
    container = soup.find(
        lambda tag: tag.name == "div"
        and tag.get("class")
        and any("archivedArticles_list" in c for c in tag.get("class"))
    )
    if not container:
        return []
    # Each card is a direct-ish child wrapping an image, a date, and a title link.
    cards = container.find_all(
        lambda tag: tag.name in ("a", "li", "div")
        and tag.find("a", href=POST_HREF_RE) is not None,
        recursive=True,
    )
    # De-duplicate nested matches (a card div and the <a> inside it both match).
    seen_hrefs = set()
    unique_cards = []
    for card in cards:
        link = card if card.name == "a" else card.find("a", href=POST_HREF_RE)
        href = link.get("href")
        if href in seen_hrefs:
            continue
        seen_hrefs.add(href)
        unique_cards.append(card)
    return unique_cards


def _extract_cards_fallback(soup: BeautifulSoup) -> list[Tag]:
    """Fallback strategy: any link on the page that looks like a post permalink,
    excluding nav/footer/header chrome."""
    for tag in soup.find_all(["nav", "header", "footer"]):
        tag.decompose()
    links = soup.find_all("a", href=POST_HREF_RE)
    return links


def parse_listing_page(soup: BeautifulSoup, page_url: str) -> list[ArticleMeta]:
    cards = _extract_cards_by_class(soup)
    if not cards:
        cards = _extract_cards_fallback(soup)

    articles: list[ArticleMeta] = []
    for card in cards:
        link = card if card.name == "a" else card.find("a", href=POST_HREF_RE)
        if not link:
            continue
        href = link.get("href")
        if not href:
            continue
        url = urljoin(BASE_URL, href)

        title = link.get_text(strip=True)
        if not title:
            # Sometimes the title is in a heading inside the link.
            heading = link.find(["h1", "h2", "h3", "h4"])
            title = heading.get_text(strip=True) if heading else ""
        if not title:
            continue

        # Look for a date near the card (in the card itself, or its parent).
        search_scope = card if card.name != "a" else (card.parent or card)
        date_match = DATE_RE.search(search_scope.get_text(" ", strip=True))
        date_text = date_match.group(0) if date_match else None

        articles.append(
            ArticleMeta(
                title=title,
                url=url,
                date=date_text,
                category=_category_from_url(url),
            )
        )
    return articles


def find_next_page_url(soup: BeautifulSoup, current_url: str) -> str | None:
    next_link = soup.find("a", string=re.compile(r"^\s*Next\s*$", re.I))
    if next_link and next_link.get("href"):
        return urljoin(BASE_URL, next_link["href"])
    return None


def iter_all_listing_pages(
    session: requests.Session,
    start_url: str = BLOG_URL,
    max_pages: int | None = None,
    delay: float = 0.5,
):
    """Yields ArticleMeta objects across every paginated listing page."""
    url = start_url
    page_count = 0
    seen_urls = set()

    while url:
        page_count += 1
        if max_pages and page_count > max_pages:
            break

        soup = _get_soup(session, url)
        articles = parse_listing_page(soup, url)

        new_articles = [a for a in articles if a.url not in seen_urls]
        if not new_articles:
            break
        for a in new_articles:
            seen_urls.add(a.url)
            yield a

        url = find_next_page_url(soup, url)
        if url:
            time.sleep(delay)  # be polite between requests


def extract_article_body(soup: BeautifulSoup) -> str:
    """Extracts the main readable text of an individual blog/release-notes post."""
    working_soup = BeautifulSoup(str(soup), "html.parser")
    for tag in working_soup.find_all(["nav", "header", "footer", "script", "style"]):
        tag.decompose()

    main = working_soup.find("main") or working_soup

    # Find the post's title heading to know where the body starts.
    title_tag = main.find(["h1", "h2"])
    if title_tag:
        parts = [title_tag.get_text(strip=True)]
        for sib in title_tag.find_all_next():
            if sib.name in ("nav", "footer"):
                break
            if sib.name in ("h3", "h4", "p", "li", "h2") and sib.get_text(strip=True):
                parts.append(sib.get_text(strip=True))
        return "\n".join(parts)

    return main.get_text("\n", strip=True)


def scrape_release_notes(
    url: str = BLOG_URL,
    category_filter: str | None = "release-notes",
    max_pages: int | None = None,
    fetch_full_body: bool = True,
) -> list[Document]:
    """
    Scrapes the Brawl Stars blog archive and returns a list of Document objects.

    Args:
        url: the listing page to start from.
        category_filter: only keep posts whose URL category segment matches this
            (e.g. "release-notes"). Pass None to keep every post (esports, etc.).
        max_pages: cap on how many paginated listing pages to walk. None = all.
        fetch_full_body: if True, visits each matching article and pulls its full
            text into page_content. If False, page_content is just the title
            (much faster, useful for just building an index).

    Returns:
        list[Document]: one Document per matching article.
    """
    documents: list[Document] = []

    with requests.Session() as session:
        metas = list(
            iter_all_listing_pages(session, start_url=url, max_pages=max_pages)
        )

        if category_filter:
            metas = [m for m in metas if m.category == category_filter]

        for meta in metas:
            if fetch_full_body:
                try:
                    article_soup = _get_soup(session, meta.url)
                    body_text = extract_article_body(article_soup)
                except requests.RequestException as e:
                    print(f"Failed to fetch {meta.url}: {e}")
                    body_text = meta.title
                time.sleep(0.5)  # be polite between requests
            else:
                body_text = meta.title

            documents.append(
                Document(
                    page_content=body_text,
                    metadata={
                        "title": meta.title,
                        "url": meta.url,
                        "date": meta.date,
                        "category": meta.category,
                    },
                )
            )

    return documents


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scrape the Brawl Stars blog.")
    parser.add_argument("--url", default=BLOG_URL, help="Listing page to start from")
    parser.add_argument(
        "--category",
        default="release-notes",
        help="Only keep this category (e.g. release-notes, esports). "
        "Pass 'all' to keep everything.",
    )
    parser.add_argument(
        "--max-pages", type=int, default=None, help="Max listing pages to walk"
    )
    parser.add_argument(
        "--no-full-body",
        action="store_true",
        help="Skip visiting each article; only collect title/url/date",
    )
    parser.add_argument(
        "--out", default="brawlstars_release_notes.json", help="Output JSON file"
    )
    args = parser.parse_args()

    category = None if args.category == "all" else args.category

    documents = scrape_release_notes(
        url=args.url,
        category_filter=category,
        max_pages=args.max_pages,
        fetch_full_body=not args.no_full_body,
    )

    print(f"Found {len(documents)} documents")

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(
            [{"metadata": d.metadata, "content": d.page_content} for d in documents],
            f,
            ensure_ascii=False,
            indent=2,
        )
    print(f"Saved to {args.out}")