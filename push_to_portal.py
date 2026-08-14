# -*- coding: utf-8 -*-
"""
Push-выгрузка результатов парсера на вебхук вашего портала
(альтернатива pull-модели через api_server.py — можно использовать обе).

Переменные окружения:
  PORTAL_WEBHOOK_URL — куда слать POST c JSON (обязательно)
  PORTAL_API_TOKEN   — Bearer-токен для заголовка Authorization (опционально)

Запуск после парсера:  python push_to_portal.py
Или одной строкой:     python parser.py && python push_to_portal.py
"""

import json
import os
import sys
from pathlib import Path

import requests

import config


def main():
    url = os.environ.get("PORTAL_WEBHOOK_URL")
    if not url:
        sys.exit("PORTAL_WEBHOOK_URL не задан — выгрузка пропущена")

    path = Path(config.OUTPUT_JSON)
    if not path.exists():
        sys.exit(f"{config.OUTPUT_JSON} не найден — сначала запустите parser.py")

    payload = json.loads(path.read_text(encoding="utf-8"))
    headers = {"Content-Type": "application/json"}
    token = os.environ.get("PORTAL_API_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"

    r = requests.post(url, json=payload, headers=headers, timeout=60)
    print(f"POST {url} → {r.status_code}")
    r.raise_for_status()
    print(f"Выгружено вакансий: {payload['total']}")


if __name__ == "__main__":
    main()
