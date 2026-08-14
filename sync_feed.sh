#!/bin/bash
# Забирает внешний фид (LinkedIn / rabota.ru / Хабр / карьерные сайты)
# из GitHub в vacancies_external.json. Локальные файлы не трогает.
set -e
cd "$(dirname "$0")"
curl -sf -o vacancies_external.json \
  "https://raw.githubusercontent.com/sobranievideopro-afk/vacancies-feed-/main/vacancies.json"
echo "$(date '+%F %T') внешний фид обновлён: $(python3 -c "import json;print(json.load(open('vacancies_external.json'))['total'])") вакансий"
# Склейка с локальным файлом отключена. Если позже понадобится единый файл —
# запустите: python3 merge_feeds.py (опционально, см. INTEGRATION.md)
