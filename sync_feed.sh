#!/bin/bash
# Забирает внешний фид (LinkedIn/rabota/Хабр/карьерные сайты) из GitHub
# и склеивает с локальным файлом hh+Telegram в общий vacancies_all.json.
# Запуск кроном на Timeweb, см. INTEGRATION.md.
set -e
cd "$(dirname "$0")"
curl -sf -o vacancies_external.json \
  "https://raw.githubusercontent.com/sobranievideopro-afk/vacancies-feed-/main/vacancies.json"
python3 merge_feeds.py
echo "$(date '+%F %T') синхронизировано: $(python3 -c "import json;print(json.load(open('vacancies_all.json'))['total'])") вакансий"
