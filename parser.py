# -*- coding: utf-8 -*-
"""
Ежедневный сборщик C-Level / Executive вакансий по России
для проекта «Кадровые резервы.РФ».

Источники (только публичные страницы, без API job-сайтов):
  - hh.ru — HTML страницы поиска
  - rabota.ru — HTML страницы поиска
  - career.habr.com — HTML страницы поиска
  - LinkedIn Jobs — публичная гостевая выдача
  - открытые карьерные сайты компаний (config.COMPANY_CAREER_PAGES)
  - публичные Telegram-каналы через t.me/s/<канал>

Запуск:  python parser.py
Выход:   vacancies.json (структурировано) + digest.md (человекочитаемый дайджест)
"""

import hashlib
import json
import re
import sys
import time
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote_plus, urljoin

import requests
from bs4 import BeautifulSoup

import config

session = requests.Session()
session.headers.update({
    "User-Agent": config.USER_AGENT,
    "Accept-Language": "ru-RU,ru;q=0.9,en;q=0.8",
})

INCLUDE_RE = [re.compile(p, re.IGNORECASE) for p in config.TITLE_INCLUDE]
EXCLUDE_RE = [re.compile(p, re.IGNORECASE) for p in config.TITLE_EXCLUDE]


# ---------------------------------------------------------------------------
# Модель данных
# ---------------------------------------------------------------------------
@dataclass
class Vacancy:
    title: str
    company: str
    url: str                       # точная HTTPS-ссылка на первоисточник
    source: str                    # hh / rabota / habr / linkedin / company / telegram
    location: str = ""
    city: str = ""          # один из config.CITIES или "Другое"
    salaryText: str = "Вознаграждение по договорённости"
    salaryLevel: int = 0           # верхняя граница в рублях; 0 = не раскрыта
    published: str = ""            # как указано в источнике
    summary: str = ""              # краткое фактическое резюме (не полный текст!)
    scopeScore: int = 0            # эвристика масштаба ответственности (0–3)
    verified: bool = False         # первоисточник открыт, пометки «в архиве» нет
    collectedAt: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(timespec="seconds")
    )

    def dedup_key(self) -> str:
        base = self.url.split("?")[0].lower() or (self.title + self.company).lower()
        return hashlib.md5(base.encode()).hexdigest()


# ---------------------------------------------------------------------------
# Утилиты
# ---------------------------------------------------------------------------
def fetch(url: str) -> str | None:
    """GET с паузой и обработкой ошибок. Возвращает HTML или None."""
    try:
        r = session.get(url, timeout=config.REQUEST_TIMEOUT, allow_redirects=True)
        time.sleep(config.PAUSE_BETWEEN_REQUESTS)
        if r.status_code != 200:
            print(f"  [!] HTTP {r.status_code}: {url}", file=sys.stderr)
            return None
        return r.text
    except requests.RequestException as e:
        print(f"  [!] Ошибка запроса {url}: {e}", file=sys.stderr)
        return None


def title_passes(title: str) -> bool:
    t = " ".join(title.split())
    if any(rx.search(t) for rx in EXCLUDE_RE):
        return False
    return any(rx.search(t) for rx in INCLUDE_RE)


SALARY_RE = re.compile(
    r"(?:от\s*)?(\d[\d\s\u00a0]{3,12})(?:\s*[-–—до]+\s*(\d[\d\s\u00a0]{3,12}))?"
    r"\s*(₽|руб|rub|\$|usd|€|eur)",
    re.IGNORECASE,
)


def parse_salary(text: str) -> tuple[str, int]:
    """Возвращает (salaryText, salaryLevel в рублях). Ничего не выдумывает."""
    if not text:
        return "Вознаграждение по договорённости", 0
    m = SALARY_RE.search(text)
    if not m:
        return "Вознаграждение по договорённости", 0
    clean = lambda s: int(re.sub(r"[\s\u00a0]", "", s))
    low = clean(m.group(1))
    high = clean(m.group(2)) if m.group(2) else low
    cur = m.group(3).lower()
    if cur in ("$", "usd"):
        rate, code = config.FX_RATES["USD"], "USD"
    elif cur in ("€", "eur"):
        rate, code = config.FX_RATES["EUR"], "EUR"
    else:
        rate, code = 1.0, "RUB"
    level = int(high * rate)
    if level < 30_000:  # защита от мусорных чисел (номера телефонов и т.п.)
        return "Вознаграждение по договорённости", 0
    return m.group(0).strip(), level


SCOPE_KEYWORDS = {
    3: [r"\bCEO\b", r"генеральн\w+ директор", r"managing director",
        r"country manager", r"general manager"],
    2: [r"\bC[FOTIMPHR]O\b", r"\bCHRO\b", r"\bCRO\b", r"\bCCO\b",
        r"исполнительн\w+ директор", r"операционн\w+ директор",
        r"коммерческ\w+ директор", r"финансов\w+ директор",
        r"техническ\w+ директор", r"директор по \w+"],
    1: [r"\bVP\b", r"vice president", r"head of"],
}


def scope_score(title: str) -> int:
    for score in (3, 2, 1):
        if any(re.search(p, title, re.IGNORECASE) for p in SCOPE_KEYWORDS[score]):
            return score
    return 0




def detect_city(*texts: str) -> str:
    """Определяет город по вхождению алиасов из config.CITIES."""
    blob = " ".join(t.lower() for t in texts if t)
    for city, meta in config.CITIES.items():
        if any(alias in blob for alias in meta["aliases"]):
            return city
    return "Другое"

def verify_source(url: str) -> tuple[bool, str]:
    """Открывает первоисточник; проверяет доступность и отсутствие «в архиве».
    Возвращает (verified, краткий_текст_страницы_для_резюме)."""
    html = fetch(url)
    if html is None:
        return False, ""
    soup = BeautifulSoup(html, "html.parser")
    page_text = soup.get_text(" ", strip=True)
    lower = page_text.lower()
    if any(marker in lower for marker in config.ARCHIVED_MARKERS):
        return False, ""
    return True, page_text[:4000]


def make_summary(title: str, company: str, page_text: str) -> str:
    """Краткое фактическое резюме без копирования полного текста."""
    if not page_text:
        return f"{title} — {company}. Детали по ссылке на первоисточник."
    # Берём первые содержательные предложения после заголовка
    sents = re.split(r"(?<=[.!?])\s+", page_text)
    picked, total = [], 0
    for s in sents:
        s = s.strip()
        if len(s) < 40 or len(s) > 300:
            continue
        picked.append(s)
        total += len(s)
        if len(picked) >= 2 or total > 400:
            break
    body = " ".join(picked)
    return f"{title} — {company}. {body}"[:500]


# ---------------------------------------------------------------------------
# Парсеры источников
# ---------------------------------------------------------------------------
def _parse_hh_html(html: str | None) -> list[Vacancy]:
    out = []
    if not html:
        return out
    soup = BeautifulSoup(html, "html.parser")
    cards = soup.select('[data-qa="serp-item"], [data-qa*="vacancy-serp__vacancy"]')
    if not cards:  # запасной селектор при смене вёрстки
        cards = [a.find_parent("div") for a in soup.select('a[href*="/vacancy/"]')]
    for card in cards:
        if card is None:
            continue
        a = card.select_one('a[data-qa*="serp-item__title"], a[href*="/vacancy/"]')
        if not a:
            continue
        title = a.get_text(" ", strip=True)
        if not title or not title_passes(title):
            continue
        url = a["href"].split("?")[0]
        comp_el = card.select_one('[data-qa*="company-name"], a[href*="/employer/"]')
        company = comp_el.get_text(" ", strip=True) if comp_el else ""
        loc_el = card.select_one('[data-qa*="address"]')
        location = loc_el.get_text(" ", strip=True) if loc_el else ""
        sal_el = card.select_one('[data-qa*="compensation"]')
        salary_text, level = parse_salary(sal_el.get_text(" ", strip=True) if sal_el else "")
        out.append(Vacancy(title=title, company=company, url=url, source="hh.ru",
                           location=location, salaryText=salary_text, salaryLevel=level,
                           scopeScore=scope_score(title)))
    return out


def parse_hh(query: str) -> list[Vacancy]:
    return _parse_hh_html(fetch(config.HH_SEARCH_URL.format(query=quote_plus(query))))


def parse_rabota(query: str) -> list[Vacancy]:
    out = []
    html = fetch(config.RABOTA_SEARCH_URL.format(query=quote_plus(query)))
    if not html:
        return out
    soup = BeautifulSoup(html, "html.parser")
    for a in soup.select('a[href*="/vacancy/"]'):
        title = a.get_text(" ", strip=True)
        if not title or not title_passes(title):
            continue
        url = urljoin("https://www.rabota.ru", a["href"].split("?")[0])
        card = a.find_parent(["article", "div"]) or a
        card_text = card.get_text(" ", strip=True)
        salary_text, level = parse_salary(card_text)
        out.append(Vacancy(title=title, company="", url=url, source="rabota.ru",
                           salaryText=salary_text, salaryLevel=level,
                           scopeScore=scope_score(title)))
    return out


def parse_habr(query: str) -> list[Vacancy]:
    out = []
    html = fetch(config.HABR_SEARCH_URL.format(query=quote_plus(query)))
    if not html:
        return out
    soup = BeautifulSoup(html, "html.parser")
    for a in soup.select('a[href^="/vacancies/"]'):
        title = a.get_text(" ", strip=True)
        if not title or not title_passes(title):
            continue
        url = urljoin("https://career.habr.com", a["href"].split("?")[0])
        out.append(Vacancy(title=title, company="", url=url, source="career.habr.com",
                           scopeScore=scope_score(title)))
    return out


def parse_linkedin_via_ddg(query: str) -> list[Vacancy]:
    """Запасной путь: публичные страницы вакансий LinkedIn через выдачу DuckDuckGo.
    Работает, когда прямой доступ к linkedin.com заблокирован (частая ситуация).
    """
    out = []
    ddg_query = quote_plus(f"site:linkedin.com/jobs {query} Russia")
    html = fetch(config.DDG_SEARCH_URL.format(query=ddg_query))
    if not html:
        return out
    soup = BeautifulSoup(html, "html.parser")
    from urllib.parse import parse_qs, unquote, urlparse
    for a in soup.select("a.result__a, h2 a"):
        href = a.get("href", "")
        # DDG оборачивает ссылки в /l/?uddg=<url> — разворачиваем
        if "uddg=" in href:
            qs = parse_qs(urlparse(href).query)
            href = unquote(qs.get("uddg", [""])[0])
        if "linkedin.com/jobs" not in href:
            continue
        title = a.get_text(" ", strip=True)
        # В заголовке выдачи обычно «Должность — Компания | LinkedIn»
        title_part = re.split(r"[|\u2013\u2014-]| in ", title)[0].strip()
        if not title_part or not title_passes(title_part):
            continue
        out.append(Vacancy(
            title=title_part,
            company=title.split("hiring")[0].strip() if "hiring" in title else "",
            url=href.split("?")[0],
            source="linkedin.com (via search)",
            scopeScore=scope_score(title_part),
        ))
    return out


def parse_linkedin(query: str) -> list[Vacancy]:
    out = []
    html = fetch(config.LINKEDIN_SEARCH_URL.format(query=quote_plus(query)))
    if not html:
        if config.LINKEDIN_FALLBACK_ENABLED:
            print("  → LinkedIn заблокировал прямой запрос, пробую через DuckDuckGo…")
            return parse_linkedin_via_ddg(query)
        return out
    soup = BeautifulSoup(html, "html.parser")
    for card in soup.select("li"):
        a = card.select_one('a[href*="/jobs/view/"], a.base-card__full-link')
        t = card.select_one("h3")
        if not a or not t:
            continue
        title = t.get_text(" ", strip=True)
        if not title_passes(title):
            continue
        comp = card.select_one("h4")
        loc = card.select_one(".job-search-card__location")
        out.append(Vacancy(
            title=title,
            company=comp.get_text(" ", strip=True) if comp else "",
            url=a["href"].split("?")[0],
            source="linkedin.com",
            location=loc.get_text(" ", strip=True) if loc else "",
            scopeScore=scope_score(title),
        ))
    if not out and config.LINKEDIN_FALLBACK_ENABLED:
        # 200 OK, но карточек нет — LinkedIn отдал заглушку. Идём в обход.
        return parse_linkedin_via_ddg(query)
    return out


def parse_company_pages() -> list[Vacancy]:
    out = []
    for site in config.COMPANY_CAREER_PAGES:
        print(f"  → карьерный сайт: {site['company']}")
        html = fetch(site["url"])
        if not html:
            continue
        soup = BeautifulSoup(html, "html.parser")
        for a in soup.find_all("a", href=True):
            title = a.get_text(" ", strip=True)
            if not title or len(title) > 120 or not title_passes(title):
                continue
            url = urljoin(site["url"], a["href"])
            if not url.startswith("https://"):
                continue
            out.append(Vacancy(title=title, company=site["company"], url=url,
                               source=f"career:{site['company']}",
                               scopeScore=scope_score(title)))
    return out


def parse_telegram_channels() -> list[Vacancy]:
    """Публичное веб-превью t.me/s/<канал> — без API и без логина."""
    out = []
    url_re = re.compile(r"https://\S+", re.IGNORECASE)
    for channel in config.TELEGRAM_CHANNELS:
        print(f"  → telegram: @{channel}")
        html = fetch(f"https://t.me/s/{channel}")
        if not html:
            continue
        soup = BeautifulSoup(html, "html.parser")
        for msg in soup.select(".tgme_widget_message"):
            text_el = msg.select_one(".tgme_widget_message_text")
            if not text_el:
                continue
            text = text_el.get_text("\n", strip=True)
            first_line = text.split("\n", 1)[0][:120]
            if not title_passes(text[:400]):
                continue
            link_el = msg.select_one("a.tgme_widget_message_date")
            msg_url = link_el["href"] if link_el else f"https://t.me/s/{channel}"
            ext = url_re.search(text)
            salary_text, level = parse_salary(text)
            out.append(Vacancy(
                title=first_line,
                company=f"@{channel}",
                url=(ext.group(0).rstrip(").,") if ext else msg_url),
                source=f"t.me/{channel}",
                salaryText=salary_text, salaryLevel=level,
                summary=text[:400],
                scopeScore=scope_score(text[:400]),
            ))
    return out


# ---------------------------------------------------------------------------
# Оркестрация
# ---------------------------------------------------------------------------
def parse_hh_city(query: str, city: str, area: int) -> list[Vacancy]:
    """Целевой поиск hh.ru по конкретному городу (area id)."""
    url = config.HH_CITY_SEARCH_URL.format(query=quote_plus(query), area=area)
    out = _parse_hh_html(fetch(url))
    for v in out:
        v.city = city
    return out


def collect() -> list[Vacancy]:
    all_v: dict[str, Vacancy] = {}

    for query in config.SEARCH_QUERIES:
        print(f"Запрос: «{query}»")
        source_map = {"hh": parse_hh, "rabota": parse_rabota,
                      "habr": parse_habr, "linkedin": parse_linkedin}
        enabled = getattr(config, "ENABLED_SOURCES",
                          ["hh", "rabota", "habr", "linkedin", "company", "telegram"])
        for name, fn in source_map.items():
            if name not in enabled:
                continue
            try:
                for v in fn(query):
                    all_v.setdefault(v.dedup_key(), v)
            except Exception as e:
                print(f"  [!] {fn.__name__}: {e}", file=sys.stderr)

    if config.PER_CITY_SEARCH and "hh" in enabled:
        print("Целевой проход по городам…")
        for city, meta in config.CITIES.items():
            print(f"  → {city}")
            for query in config.CITY_SEARCH_QUERIES:
                try:
                    for v in parse_hh_city(query, city, meta["hh_area"]):
                        all_v.setdefault(v.dedup_key(), v)
                except Exception as e:
                    print(f"  [!] hh {city}: {e}", file=sys.stderr)

    if "company" in enabled:
        print("Карьерные сайты компаний…")
        for v in parse_company_pages():
            all_v.setdefault(v.dedup_key(), v)

    if "telegram" in enabled and config.TELEGRAM_CHANNELS:
        print("Telegram-каналы…")
        for v in parse_telegram_channels():
            all_v.setdefault(v.dedup_key(), v)

    return list(all_v.values())


def verify_all(vacancies: list[Vacancy]) -> list[Vacancy]:
    if not config.VERIFY_SOURCE_PAGES:
        for v in vacancies:
            v.verified = True
        return vacancies
    ok = []
    print(f"Проверка первоисточников: {len(vacancies)} шт…")
    for v in vacancies:
        verified, page_text = verify_source(v.url)
        if not verified:
            print(f"  [архив/недоступна] {v.title} — {v.url}")
            continue
        v.verified = True
        if not v.summary:
            v.summary = make_summary(v.title, v.company, page_text)
        if v.salaryLevel == 0:  # попытка найти зарплату на странице вакансии
            s_text, s_level = parse_salary(page_text)
            if s_level:
                v.salaryText, v.salaryLevel = s_text, s_level
        ok.append(v)
    return ok


def sort_vacancies(vacancies: list[Vacancy]) -> list[Vacancy]:
    """Приоритет: раскрытая зарплата и её верхняя граница → свежесть → масштаб."""
    return sorted(
        vacancies,
        key=lambda v: (v.salaryLevel > 0, v.salaryLevel, v.collectedAt, v.scopeScore),
        reverse=True,
    )


def load_seen(path: Path) -> set[str]:
    if path.exists():
        return set(json.loads(path.read_text(encoding="utf-8")))
    return set()


def write_outputs(vacancies: list[Vacancy]):
    by_city: dict[str, list[str]] = {}
    for v in vacancies:
        by_city.setdefault(v.city or "Другое", []).append(v.url)
    payload = {
        "generatedAt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "total": len(vacancies),
        "cities": {c: len(urls) for c, urls in sorted(by_city.items())},
        "vacancies": [asdict(v) for v in vacancies],
    }
    Path(config.OUTPUT_JSON).write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [f"# Дайджест C-Level вакансий — {datetime.now():%d.%m.%Y}\n"]
    order = list(config.CITIES.keys()) + ["Другое"]
    grouped: dict[str, list[Vacancy]] = {}
    for v in vacancies:
        grouped.setdefault(v.city or "Другое", []).append(v)
    for city in order:
        if city not in grouped:
            continue
        lines.append(f"\n## {city} — {len(grouped[city])}\n")
        for i, v in enumerate(grouped[city], 1):
            lines.append(
                f"**{i}. {v.title}** — {v.company or '—'} ({v.source})\n"
                f"Зарплата: {v.salaryText}\n"
                f"{v.summary}\n"
                f"Ссылка: {v.url}\n")
    Path(config.OUTPUT_DIGEST).write_text("\n".join(lines), encoding="utf-8")


def main():
    seen_path = Path(config.SEEN_FILE)
    seen = load_seen(seen_path)

    vacancies = collect()
    print(f"Собрано до дедупликации между запусками: {len(vacancies)}")

    fresh = [v for v in vacancies if v.dedup_key() not in seen]
    print(f"Новых с прошлого запуска: {len(fresh)}")

    fresh = verify_all(fresh)
    for v in fresh:
        if not v.city:
            v.city = detect_city(v.location, v.title, v.summary)
    fresh = sort_vacancies(fresh)

    write_outputs(fresh)
    seen |= {v.dedup_key() for v in fresh}
    seen_path.write_text(json.dumps(sorted(seen)), encoding="utf-8")

    print(f"Готово: {len(fresh)} вакансий → {config.OUTPUT_JSON}, {config.OUTPUT_DIGEST}")


if __name__ == "__main__":
    main()
