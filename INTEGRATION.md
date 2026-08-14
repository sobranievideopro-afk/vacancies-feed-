# Подключение парсера к порталу «Кадровые резервы.РФ»

## Архитектура

```
┌─ Railway ────────────────────────────────────────────┐
│  Сервис 1 (worker): scheduler.py — парсинг в 12:00   │
│        │  пишет vacancies.json + digest.md в volume  │
│  Сервис 2 (web): api_server.py — REST API            │
│        │  читает vacancies.json из того же volume    │
└────────┼─────────────────────────────────────────────┘
         ▼
  Портал (Tilda / ваш фронт) → fetch(API) → карточки вакансий
```

Обе модели поддержаны: **pull** (портал сам ходит в API) и
**push** (`push_to_portal.py` шлёт JSON на ваш вебхук после каждого прогона).

## Формат данных (vacancies.json)

```json
{
  "generatedAt": "2026-08-09T09:00:00+00:00",
  "total": 143,
  "cities": {"Москва": 78, "Санкт-Петербург": 22, "Другое": 15},
  "vacancies": [
    {
      "title": "Генеральный директор",
      "company": "ООО Компания",
      "url": "https://hh.ru/vacancy/123456",
      "source": "hh.ru",
      "location": "Москва",
      "city": "Москва",
      "salaryText": "800 000 – 850 000 ₽",
      "salaryLevel": 850000,
      "published": "",
      "summary": "Краткое фактическое резюме…",
      "scopeScore": 3,
      "verified": true,
      "collectedAt": "2026-08-09T08:55:12+00:00"
    }
  ]
}
```

`salaryLevel = 0` означает «Вознаграждение по договорённости».
`city` — один из 15 городов из config.CITIES либо «Другое».

## API (api_server.py)

| Эндпоинт | Описание |
|---|---|
| `GET /health` | статус + готовность данных |
| `GET /api/vacancies` | все вакансии, сортировка парсера сохранена |
| `GET /api/vacancies?city=Москва&minSalary=500000&q=CEO&limit=20&offset=0` | фильтры + пагинация |
| `GET /api/cities` | города со счётчиками |
| `GET /api/digest` | Markdown-дайджест (для Telegram-бота) |

## Виджет для Tilda (вставить в блок T123 «HTML-код»)

```html
<div id="kr-vacancies"></div>
<script>
const API = "https://ВАШ-СЕРВИС.up.railway.app";
fetch(API + "/api/vacancies?limit=10")
  .then(r => r.json())
  .then(d => {
    document.getElementById("kr-vacancies").innerHTML = d.items.map(v => `
      <div style="border:1px solid #e5e5e5;border-radius:12px;padding:16px;margin:8px 0">
        <b>${v.title}</b> — ${v.company || "компания не раскрыта"}<br>
        <span style="color:#2a7">${v.salaryText}</span> · ${v.city} · ${v.source}<br>
        <a href="${v.url}" target="_blank" rel="noopener">Открыть вакансию →</a>
      </div>`).join("");
  })
  .catch(() => {
    document.getElementById("kr-vacancies").innerText = "Вакансии временно недоступны";
  });
</script>
```

## Деплой на Railway

1. Один проект, два сервиса из этой же папки:
   - **worker**: Start Command `python scheduler.py`, переменные
     `TZ=Europe/Moscow`, `RUN_AT=12:00`
   - **web**: Start Command `uvicorn api_server:app --host 0.0.0.0 --port $PORT`,
     переменная `ALLOWED_ORIGINS=https://кадровыерезервы.рф` (ваш домен)
2. Общий **Volume**, смонтированный в рабочую папку обоих сервисов —
   в нём живут `vacancies.json`, `digest.md` и `seen.json` (дедупликация).
3. Push-модель (опционально): в worker добавьте переменные
   `PORTAL_WEBHOOK_URL` и `PORTAL_API_TOKEN`, а запуск замените на
   `python scheduler.py` с вызовом `push_to_portal.py` внутри — или
   используйте Railway Cron вместо scheduler:

   **Вариант с Railway Cron (проще):** один сервис, Cron Schedule
   `0 9 * * *` (09:00 UTC = 12:00 МСК), Start Command
   `python parser.py && python push_to_portal.py`.

## Обычный сервер (VPS)

```bash
crontab -e
0 12 * * * cd /path/to/vacancy_parser && /usr/bin/python3 parser.py && /usr/bin/python3 push_to_portal.py >> parser.log 2>&1
```

## Замечания

- Первый прогон с PER_CITY_SEARCH=True делает ~150 дополнительных запросов
  к hh.ru (15 городов × 9 запросов) с паузой 3 с — это ~8 минут сверху.
  Если словите капчу, поставьте PER_CITY_SEARCH=False: города продолжат
  определяться из текста общероссийской выдачи.
- Карьерные сайты-SPA (Яндекс, Ozon и др.) могут отдавать пустую первичную
  вёрстку — см. комментарий в config.py, это ограничение подхода без браузера.
