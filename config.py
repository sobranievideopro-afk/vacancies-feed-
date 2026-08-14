# -*- coding: utf-8 -*-
"""
Конфигурация парсера C-Level вакансий для проекта «Кадровые резервы.РФ».
Все источники — только публично доступные страницы, без API job-сайтов
и без авторизованной браузерной автоматизации.
"""


# ---------------------------------------------------------------------------
# Какие источники включены НА ЭТОМ сервере.
# hh.ru и Telegram намеренно НЕ входят: их покрывает отдельная
# связка на сервере пользователя (Timeweb).
# Возможные значения: "rabota", "habr", "linkedin", "company"
# ---------------------------------------------------------------------------
ENABLED_SOURCES = ["rabota", "habr", "linkedin", "company", "superjob", "executive"]

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
    "Москва":           {"hh_area": 1,   "aliases": ["москв", "moscow", "мск"]},
    "Санкт-Петербург":  {"hh_area": 2,   "aliases": ["санкт-петербург", "петербург", "спб", "saint petersburg"]},
    "Новосибирск":      {"hh_area": 4,   "aliases": ["новосибирск", "novosibirsk"]},
    "Екатеринбург":     {"hh_area": 3,   "aliases": ["екатеринбург", "ekaterinburg"]},
    "Казань":           {"hh_area": 88,  "aliases": ["казан", "kazan"]},
    "Нижний Новгород":  {"hh_area": 66,  "aliases": ["нижний новгород", "nizhny novgorod"]},
    "Краснодар":        {"hh_area": 53,  "aliases": ["краснодар", "krasnodar"]},
    "Самара":           {"hh_area": 78,  "aliases": ["самар", "samara"]},
    "Ростов-на-Дону":   {"hh_area": 76,  "aliases": ["ростов-на-дону", "ростов", "rostov"]},
    "Уфа":              {"hh_area": 99,  "aliases": ["уфа", "уфе", "уфы", "ufa"]},
    "Челябинск":        {"hh_area": 104, "aliases": ["челябинск", "chelyabinsk"]},
    "Пермь":            {"hh_area": 72,  "aliases": ["перм", "perm"]},
    "Воронеж":          {"hh_area": 26,  "aliases": ["воронеж", "voronezh"]},
    "Красноярск":       {"hh_area": 54,  "aliases": ["красноярск", "krasnoyarsk"]},
    "Владивосток":      {"hh_area": 22,  "aliases": ["владивосток", "vladivostok"]},
}
# area id можно сверить в открытом справочнике: https://api.hh.ru/areas

# Города используются для распознавания из текста вакансии (поле city).


# ---------------------------------------------------------------------------
# Дополнительные порталы вакансий (не job-API, обычные страницы поиска).
# career.ru и hh.ru/career сюда намеренно не входят — это hh.ru под другим
# именем/его собственная страница найма, а hh.ru ведёт отдельный скрипт.
# ---------------------------------------------------------------------------
SUPERJOB_SEARCH_URL = "https://www.superjob.ru/vacancy/search/?keywords[0][keys]={query}"
EXECUTIVE_RU_JOBS_URL = "https://www.e-xecutive.ru/jobs"
WORK_RU_SEARCH_URL = "https://www.work.ru/resume/search/?q={query}"  # неверифицировано, проверить на первом прогоне

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
    # Приоритетные компании пользователя
    {"company": "Mars",           "url": "https://rus.mars.com/careers"},
    {"company": "2ГИС",           "url": "https://hr.2gis.ru/vacancies"},
    {"company": "Логика Молока",  "url": "https://logikamoloka.ru/career"},
    {"company": "Точка",          "url": "https://tochka.com/hiring/"},
    # Корпоративный список — проверен и исправлен:
    {"company": "Яндекс",         "url": "https://yandex.ru/jobs/vacancies"},
    {"company": "Сбер",           "url": "https://sber.ru/ru/careers"},
    {"company": "Газпром нефть",  "url": "https://gpn-career.ru"},
    {"company": "МТС",            "url": "https://mts.ru/careers"},
    {"company": "Северсталь",     "url": "https://career.severstal.com/vacancies/"},
    {"company": "Т-Банк",         "url": "https://www.tbank.ru/career/vacancies/"},
    {"company": "ВТБ",            "url": "https://vtb.ru/career/"},
    {"company": "Магнит",         "url": "https://rabota.magnit.ru/vacancy/"},
    {"company": "X5 Group",       "url": "https://x5.ru/careers"},
    {"company": "Ростелеком",     "url": "https://rt.ru/career"},
    {"company": "Аэрофлот",       "url": "https://www.aeroflot.ru/ru/jobs"},
    {"company": "МТС Банк",       "url": "https://www.mtsbank.ru/o-banke/career/"},
    {"company": "Ozon",           "url": "https://job.ozon.ru/vacancies"},
    {"company": "VK",             "url": "https://team.vk.company/vacancy/"},
    {"company": "Росатом",        "url": "https://rosatom-career.ru/vacancies"},
    {"company": "СИБУР",          "url": "https://career.sibur.ru/vacancies/"},
    {"company": "Авито",          "url": "https://career.avito.com/vacancies/"},
    # Danone и Heineken свернули розничный бизнес в РФ (2023-2024) — карьерные
    # страницы могут быть недействующими; оставлены с пометкой, парсер
    # просто получит нулевую выдачу если сайт не отвечает.
    {"company": "Danone",         "url": "https://danone.ru/career", "uncertain": True},
    {"company": "Heineken",       "url": "https://heineken.ru/ru/careers", "uncertain": True},
    # НЕ включены из списка пользователя:
    #  - HeadHunter career.ru — технически алиас hh.ru, исключён вместе с hh.ru
    #  - hh.ru/career, superjob.ru/career — это страницы "работа у нас" самих
    #    порталов, а не каталоги вакансий других компаний
    # Многие карьерные разделы — SPA на JS; нулевая выдача по компании ожидаема.
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
