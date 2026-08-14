# -*- coding: utf-8 -*-
"""
Конфигурация парсера C-Level вакансий для проекта «Кадровые резервы.РФ».
Все источники — только публично доступные страницы, без API job-сайтов
и без авторизованной браузерной автоматизации.
"""

# ---------------------------------------------------------------------------
# Поисковые запросы (используются для hh.ru, rabota.ru, career.habr.com, LinkedIn)
# ---------------------------------------------------------------------------
SEARCH_QUERIES = [
    "генеральный директор",
    "исполнительный директор",
    "управляющий директор",
    "операционный директор",
    "коммерческий директор",
    "финансовый директор",
    "технический директор",
    "директор по маркетингу",
    "директор по персоналу",
    "директор по продукту",
    "CEO", "COO", "CFO", "CTO", "CIO", "CMO", "CPO", "CHRO", "CRO", "CCO",
    "Managing Director", "Country Manager", "General Manager",
    "VP", "Head of",
]

# ---------------------------------------------------------------------------
# Крупные города России: имя → area id на hh.ru (для целевого поиска)
# и варианты написания для распознавания города в тексте вакансии.
# ---------------------------------------------------------------------------
CITIES = {
    "Москва":           {"hh_area": 1,   "aliases": ["москва", "moscow", "мск"]},
    "Санкт-Петербург":  {"hh_area": 2,   "aliases": ["санкт-петербург", "петербург", "спб", "saint petersburg"]},
    "Новосибирск":      {"hh_area": 4,   "aliases": ["новосибирск", "novosibirsk"]},
    "Екатеринбург":     {"hh_area": 3,   "aliases": ["екатеринбург", "ekaterinburg"]},
    "Казань":           {"hh_area": 88,  "aliases": ["казань", "kazan"]},
    "Нижний Новгород":  {"hh_area": 66,  "aliases": ["нижний новгород", "nizhny novgorod"]},
    "Краснодар":        {"hh_area": 53,  "aliases": ["краснодар", "krasnodar"]},
    "Самара":           {"hh_area": 78,  "aliases": ["самара", "samara"]},
    "Ростов-на-Дону":   {"hh_area": 76,  "aliases": ["ростов-на-дону", "ростов", "rostov"]},
    "Уфа":              {"hh_area": 99,  "aliases": ["уфа", "ufa"]},
    "Челябинск":        {"hh_area": 104, "aliases": ["челябинск", "chelyabinsk"]},
    "Пермь":            {"hh_area": 72,  "aliases": ["пермь", "perm"]},
    "Воронеж":          {"hh_area": 26,  "aliases": ["воронеж", "voronezh"]},
    "Красноярск":       {"hh_area": 54,  "aliases": ["красноярск", "krasnoyarsk"]},
    "Владивосток":      {"hh_area": 22,  "aliases": ["владивосток", "vladivostok"]},
}
# area id можно сверить в открытом справочнике: https://api.hh.ru/areas

# Целевой поиск по каждому городу отдельно (точнее, но больше запросов).
# При False города определяются только из текста общероссийской выдачи.
PER_CITY_SEARCH = True
# Для по-городового прохода — сокращённый список запросов,
# чтобы не превышать разумное число обращений (иначе капча):
CITY_SEARCH_QUERIES = [
    "генеральный директор", "исполнительный директор", "операционный директор",
    "коммерческий директор", "финансовый директор", "технический директор",
    "CEO", "директор по маркетингу", "директор по персоналу",
]
HH_CITY_SEARCH_URL = (
    "https://hh.ru/search/vacancy?text={query}"
    "&area={area}&search_field=name&order_by=publication_time&items_on_page=50"
)

# ---------------------------------------------------------------------------
# Фильтры по названию должности
# ---------------------------------------------------------------------------
TITLE_INCLUDE = [
    r"\bCEO\b", r"\bCOO\b", r"\bCFO\b", r"\bCTO\b", r"\bCIO\b", r"\bCMO\b",
    r"\bCPO\b", r"\bCHRO\b", r"\bCRO\b", r"\bCCO\b",
    r"генеральн\w+ директор", r"исполнительн\w+ директор",
    r"управляющ\w+ директор", r"операционн\w+ директор",
    r"коммерческ\w+ директор", r"финансов\w+ директор",
    r"техническ\w+ директор",
    r"директор по \w+",
    r"managing director", r"country manager", r"general manager",
    r"\bVP\b", r"vice president",
    r"head of \w+", r"руководитель направлени", r"руководитель функции",
]

TITLE_EXCLUDE = [
    r"ассистент", r"помощник", r"assistant", r"секретар",
    r"директор магазина", r"директор ресторана", r"директор филиала",
    r"директор офиса продаж", r"директор склада", r"директор кафе",
    r"директор салона", r"директор клиники",  # без стратегической ответственности
    r"заместител[ья] директора магазина",
    r"стажер", r"trainee", r"intern",
]

# ---------------------------------------------------------------------------
# Источники: страницы поиска
# ---------------------------------------------------------------------------
# area=113 — Россия; order_by=publication_time — свежие первыми
HH_SEARCH_URL = (
    "https://hh.ru/search/vacancy?text={query}"
    "&area=113&search_field=name&order_by=publication_time&items_on_page=50"
)

RABOTA_SEARCH_URL = "https://www.rabota.ru/vacancy?query={query}&sort=relevance"

HABR_SEARCH_URL = "https://career.habr.com/vacancies?q={query}&type=all"

# Публичная (гостевая) HTML-выдача LinkedIn Jobs, без авторизации.
# Внимание: LinkedIn агрессивно ограничивает частоту запросов — держите паузы.
LINKEDIN_SEARCH_URL = (
    "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
    "?keywords={query}&location=Russia&start=0"
)

# Запасной путь для LinkedIn: если гостевая выдача заблокировала запрос,
# ищем публичные страницы вакансий LinkedIn через HTML-выдачу DuckDuckGo
# (не требует API-ключа). Извлекаются только ссылки вида linkedin.com/jobs/.
LINKEDIN_FALLBACK_ENABLED = True
DDG_SEARCH_URL = "https://html.duckduckgo.com/html/?q={query}"

# ---------------------------------------------------------------------------
# Открытые карьерные сайты компаний (страница со списком вакансий)
# Парсятся универсальным методом: собираются ссылки, текст которых
# проходит фильтр TITLE_INCLUDE.
# ---------------------------------------------------------------------------
COMPANY_CAREER_PAGES = [
    # Ваши приоритетные компании
    {"company": "Mars",           "url": "https://rus.mars.com/careers"},
    {"company": "2ГИС",           "url": "https://hr.2gis.ru/vacancies"},
    {"company": "Логика Молока",  "url": "https://logikamoloka.ru/career"},
    {"company": "Т-Банк",         "url": "https://www.tbank.ru/career/vacancies/"},
    {"company": "Точка",          "url": "https://tochka.com/hiring/"},
    # Топ-компании России (открытые карьерные разделы)
    {"company": "Сбер",           "url": "https://rabota.sber.ru/vacancies"},
    {"company": "Яндекс",         "url": "https://yandex.ru/jobs/vacancies"},
    {"company": "VK",             "url": "https://team.vk.company/vacancy/"},
    {"company": "МТС",            "url": "https://job.mts.ru/vacancies"},
    {"company": "МегаФон",        "url": "https://job.megafon.ru/vacancy"},
    {"company": "Ozon",           "url": "https://job.ozon.ru/vacancies"},
    {"company": "X5 Group",       "url": "https://rabota.x5.ru/vacancies"},
    {"company": "Магнит",         "url": "https://rabota.magnit.ru/vacancy/"},
    {"company": "Росатом",        "url": "https://rosatom-career.ru/vacancies"},
    {"company": "СИБУР",          "url": "https://career.sibur.ru/vacancies/"},
    {"company": "Северсталь",     "url": "https://career.severstal.com/vacancies/"},
    {"company": "Авито",          "url": "https://career.avito.com/vacancies/"},
    # ВАЖНО: часть этих сайтов — SPA на JavaScript. Универсальный HTML-парсер
    # соберёт с них только то, что есть в первичной вёрстке; если карьерный
    # раздел рендерится целиком на клиенте, вакансии с него не подтянутся —
    # это ожидаемое ограничение подхода «без браузерной автоматизации».
    # URL со временем меняются — при нулевой выдаче по компании проверьте адрес.
]

# ---------------------------------------------------------------------------
# Telegram: публичные каналы с вакансиями.
# Читаются через публичное веб-превью t.me/s/<канал> — без API и без логина.
# Укажите каналы, за которыми хотите следить (без @).
# ---------------------------------------------------------------------------
TELEGRAM_CHANNELS = [
    "toplevel_job",           # TOP LEVEL JOB — вакансии для руководителей, ~20K подписчиков
    "middle_top_vacancies",   # Вакансии для миддл и топ-менеджеров от $2500
    # добавляйте свои каналы (имя без @):
]

# ---------------------------------------------------------------------------
# Прочее
# ---------------------------------------------------------------------------
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)

REQUEST_TIMEOUT = 20          # секунд
PAUSE_BETWEEN_REQUESTS = 3.0  # секунд — не снижайте, чтобы не ловить баны
VERIFY_SOURCE_PAGES = True    # открывать каждую вакансию и проверять «в архиве»

# Курсы для нормализации зарплат к рублю (обновляйте при необходимости)
FX_RATES = {"RUB": 1.0, "USD": 90.0, "EUR": 98.0}

# Маркеры закрытой/архивной вакансии на странице первоисточника
ARCHIVED_MARKERS = [
    "в архиве", "вакансия закрыта", "вакансия в архиве",
    "vacancy archived", "no longer accepting", "expired",
    "вакансия не найдена", "страница не найдена",
]

OUTPUT_JSON = "vacancies.json"
OUTPUT_DIGEST = "digest.md"
SEEN_FILE = "seen.json"       # дедупликация между запусками
