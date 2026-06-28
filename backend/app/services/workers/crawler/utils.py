import hashlib
import logging
import random
import trafilatura
from typing import Optional
from urllib.parse import urljoin, urlparse, urlunparse
import httpx
from bs4 import BeautifulSoup
from app.core.config import settings
from app.helpers.proxy_helper import StaticListProxyProvider

logger = logging.getLogger("arionex.crawler_service")

_DEFAULT_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "fa,en;q=0.9",
}

_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 Edg/122.0.0.0"
]

_SEMANTIC_TAGS = [
    "article", "main", "section", "p", "h1", "h2", "h3",
    "h4", "h5", "h6", "li", "td", "th", "blockquote", "figcaption"
]

_BLOCKED_DOMAINS = {
    "google.com", "facebook.com", "twitter.com", "instagram.com",
    "youtube.com", "linkedin.com", "t.me", "telegram.org",
    "gstatic.com", "googleapis.com", "cloudflare.com",
    "jquery.com", "bootstrap.com", "cdnjs.cloudflare.com",
}

_SKIP_EXTENSIONS = {
    ".jpg", ".jpeg", ".png", ".gif", ".svg", ".webp", ".ico",
    ".pdf", ".zip", ".rar", ".tar", ".gz", ".exe", ".dmg",
    ".mp4", ".mp3", ".avi", ".mov", ".wav", ".ogg",
    ".css", ".js", ".json", ".xml", ".rss", ".atom",
    ".woff", ".woff2", ".ttf", ".eot", ".otf",
}

_proxy_provider = StaticListProxyProvider(settings.crawler.proxy_pool)


def _normalize_url(url: str) -> str:
    parsed = urlparse(url)
    normalized = parsed._replace(fragment="", query="")
    return urlunparse(normalized).rstrip("/")


def _is_same_domain(base_url: str, target_url: str) -> bool:
    base_domain = urlparse(base_url).netloc.lower().lstrip("www.")
    target_domain = urlparse(target_url).netloc.lower().lstrip("www.")
    return target_domain == base_domain or target_domain.endswith(f".{base_domain}")


def _is_skippable_url(url: str) -> bool:
    parsed = urlparse(url)
    path_lower = parsed.path.lower()
    for ext in _SKIP_EXTENSIONS:
        if path_lower.endswith(ext):
            return True
    if parsed.scheme in ("mailto", "tel", "javascript", "data"):
        return True
    return False


def _is_blocked_domain(url: str) -> bool:
    domain = urlparse(url).netloc.lower().lstrip("www.")
    for blocked in _BLOCKED_DOMAINS:
        if domain == blocked or domain.endswith(f".{blocked}"):
            return True
    return False


def _score_external_url_relevance(base_domain: str, target_url: str) -> float:
    if _is_blocked_domain(target_url):
        return 0.0

    target_domain = urlparse(target_url).netloc.lower().lstrip("www.")
    base_root = ".".join(base_domain.rsplit(".", 2)[-2:])
    target_root = ".".join(target_domain.rsplit(".", 2)[-2:])

    if target_root == base_root:
        return 0.9

    return 0.3


async def _fetch_page_plain(url: str, proxy: Optional[str] = None, user_agent: Optional[str] = None) -> Optional[str]:
    headers = _DEFAULT_HEADERS.copy()
    headers["User-Agent"] = user_agent or random.choice(_USER_AGENTS)

    try:
        async with httpx.AsyncClient(headers=headers, proxy=proxy, verify=True, timeout=15.0) as client:
            response = await client.get(url, follow_redirects=True)
            if response.status_code == 200:
                content_type = response.headers.get("content-type", "")
                if "text/html" in content_type:
                    return response.text
            logger.debug(f"Skipping non-HTML response from {url} (status={response.status_code})")
            return None
    except httpx.TimeoutException:
        logger.warning(f"Timeout fetching page: {url}")
        return None
    except httpx.TooManyRedirects:
        logger.warning(f"Too many redirects: {url}")
        return None
    except Exception as e:
        logger.warning(f"Failed to fetch page {url} (proxy={proxy}): {str(e)}")
        if proxy:
            _proxy_provider.report_failure(proxy)
        return None


async def _fetch_page_js(url: str, proxy: Optional[str] = None, user_agent: Optional[str] = None) -> Optional[str]:
    try:
        from playwright.async_api import async_playwright
        async with async_playwright() as p:
            playwright_proxy = None
            if proxy:
                playwright_proxy = {"server": proxy}

            browser = await p.chromium.launch(headless=True, proxy=playwright_proxy)
            context = await browser.new_context(
                user_agent=user_agent or random.choice(_USER_AGENTS),
                locale="fa-IR"
            )
            page = await context.new_page()
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            # یک صبر کوتاه برای تکمیل رندر المان‌های جاوااسکریپت پس از لود DOM
            await page.wait_for_timeout(3000)
            html = await page.content()
            await browser.close()
            return html
    except ImportError:
        logger.error("Playwright is not installed. Run: pip install playwright && playwright install chromium")
        return None
    except Exception as e:
        logger.warning(f"Playwright failed to render {url} (proxy={proxy}): {str(e)}")
        if proxy:
            _proxy_provider.report_failure(proxy)
        return None


def _extract_page_content(html: str, url: str) -> dict:
    # Use trafilatura to extract clean main text and metadata
    res = trafilatura.bare_extraction(html, url=url, include_links=False)
    
    title = ""
    description = ""
    body_text = ""
    
    if res:
        if isinstance(res, dict):
            title = res.get("title") or ""
            description = res.get("description") or ""
            body_text = res.get("text") or ""
        else:
            title = getattr(res, "title", "") or ""
            description = getattr(res, "description", "") or ""
            body_text = getattr(res, "text", "") or ""

    # Fallback to BeautifulSoup if body text is empty
    if not body_text.strip():
        logger.debug(f"Trafilatura failed or returned empty text for {url}. Falling back to BeautifulSoup.")
        soup = BeautifulSoup(html, "lxml")
        
        # Decompose unnecessary elements
        for tag in soup(["script", "style", "nav", "footer", "header",
                         "aside", "noscript", "iframe", "form",
                         "button", "input", "select", "textarea"]):
            tag.decompose()
            
        if not title and soup.title and soup.title.string:
            title = soup.title.string.strip()
            
        if not description:
            meta_desc = soup.find("meta", attrs={"name": "description"})
            if meta_desc and meta_desc.get("content"):
                description = meta_desc["content"].strip()
            if not description:
                og_desc = soup.find("meta", property="og:description")
                if og_desc and og_desc.get("content"):
                    description = og_desc["content"].strip()
                    
        body_parts = []
        for tag in soup.find_all(_SEMANTIC_TAGS):
            text = tag.get_text(separator=" ", strip=True)
            if text and len(text) > 30:
                body_parts.append(text)
                
        seen = set()
        unique_parts = []
        for part in body_parts:
            part_hash = hashlib.md5(part.encode()).hexdigest()
            if part_hash not in seen:
                seen.add(part_hash)
                unique_parts.append(part)
                
        body_text = "\n".join(unique_parts)
    else:
        # If trafilatura succeeded, ensure we still populate title/desc from BeautifulSoup if they are missing
        if not title or not description:
            soup = BeautifulSoup(html, "lxml")
            if not title and soup.title and soup.title.string:
                title = soup.title.string.strip()
            if not description:
                meta_desc = soup.find("meta", attrs={"name": "description"})
                if meta_desc and meta_desc.get("content"):
                    description = meta_desc["content"].strip()

    # Extract outgoing links
    soup = BeautifulSoup(html, "lxml")
    outgoing_links = set()
    for a_tag in soup.find_all("a", href=True):
        href = a_tag["href"].strip()
        if not href or href.startswith("#"):
            continue
        try:
            absolute_url = urljoin(url, href)
            if urlparse(absolute_url).scheme in ("http", "https"):
                normalized = _normalize_url(absolute_url)
                outgoing_links.add(normalized)
        except Exception:
            continue

    # Compile the final text format
    full_content_parts = []
    if title:
        full_content_parts.append(f"عنوان صفحه: {title}")
    if description:
        full_content_parts.append(f"توضیح: {description}")
    if body_text:
        full_content_parts.append(body_text)
        
    full_text = "\n\n".join(full_content_parts)

    return {
        "title": title,
        "description": description,
        "body_text": full_text,
        "outgoing_links": outgoing_links,
    }


def _check_robots_txt_sync(base_url: str, target_url: str, proxy: Optional[str] = None) -> bool:
    try:
        from robotexclusionrulesparser import RobotExclusionRulesParser
        import requests as sync_requests
        parsed = urlparse(base_url)
        robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
        
        proxies = None
        if proxy:
            proxies = {"http": proxy, "https": proxy}

        resp = sync_requests.get(
            robots_url,
            timeout=5,
            headers={"User-Agent": random.choice(_USER_AGENTS)},
            proxies=proxies
        )
        if resp.status_code == 200:
            rerp = RobotExclusionRulesParser()
            rerp.parse(resp.text)
            return rerp.is_allowed("ArioNexBot/1.0", target_url)
        return True
    except Exception as e:
        logger.debug(f"robots.txt check failed for {base_url}: {str(e)}")
        return True
