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

## Деплой на Timeweb VPS (Ubuntu)

Код уже в вашем GitHub — на сервере всё разворачивается пятью командами:

```bash
# 1. Зайти на сервер
ssh root@ВАШ_IP

# 2. Установить зависимости и склонировать репозиторий
apt update && apt install -y python3-pip git
git clone https://github.com/sobranievideopro-afk/vacancies-feed-.git /opt/vacancy_parser
cd /opt/vacancy_parser && pip3 install -r requirements.txt

# 3. Проверить разовый запуск (соберёт hh.ru + Telegram)
python3 parser.py

# 4. Автозапуск ежедневно в 12:00 по Москве
timedatectl set-timezone Europe/Moscow
(crontab -l 2>/dev/null; echo "0 12 * * * cd /opt/vacancy_parser && /usr/bin/python3 parser.py >> parser.log 2>&1") | crontab -
```

В `config.py` уже стоит `ENABLED_SOURCES = ["hh", "telegram"]` — на этом
сервере работают только hh.ru и Telegram. Остальные источники (LinkedIn,
rabota.ru, Хабр, карьерные сайты) публикуются внешним сборщиком в тот же
GitHub-репозиторий (vacancies.json), портал склеивает оба файла.
Чтобы не перезаписывать внешний файл, задайте на сервере своё имя выхода
в config.py: `OUTPUT_JSON = "vacancies_hh_tg.json"`.

### REST API на этом же сервере (опционально)

```bash
# systemd-сервис, чтобы API жил постоянно и поднимался после ребута
cat > /etc/systemd/system/vacancy-api.service << 'UNIT'
[Unit]
Description=Kadrovye Rezervy Vacancy API
After=network.target

[Service]
WorkingDirectory=/opt/vacancy_parser
ExecStart=/usr/bin/python3 -m uvicorn api_server:app --host 0.0.0.0 --port 8080
Restart=always
Environment=ALLOWED_ORIGINS=https://xn----dtbhcmta3agdgke1a8k.xn--p1ai

[Install]
WantedBy=multi-user.target
UNIT
systemctl daemon-reload && systemctl enable --now vacancy-api
```

API будет доступен на `http://ВАШ_IP:8080/api/vacancies`. Для HTTPS
поставьте сверху nginx + certbot или проксируйте через панель Timeweb.

### Обновление кода на сервере

```bash
cd /opt/vacancy_parser && git pull
```

## Замечания

- Первый прогон с PER_CITY_SEARCH=True делает ~150 дополнительных запросов
  к hh.ru (15 городов × 9 запросов) с паузой 3 с — это ~8 минут сверху.
  Если словите капчу, поставьте PER_CITY_SEARCH=False: города продолжат
  определяться из текста общероссийской выдачи.
- Карьерные сайты-SPA (Яндекс, Ozon и др.) могут отдавать пустую первичную
  вёрстку — см. комментарий в config.py, это ограничение подхода без браузера.
