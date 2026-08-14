# -*- coding: utf-8 -*-
"""
Автозапуск парсера ежедневно в 12:00 (локальное время сервера).

Запуск:  python scheduler.py
Время меняется переменной окружения RUN_AT (формат HH:MM), напр. RUN_AT=09:30.
Часовой пояс сервера задаётся переменной TZ (на Railway: TZ=Europe/Moscow).

Альтернатива без постоянного процесса — системный cron или Railway Cron
(см. INTEGRATION.md), тогда этот файл не нужен.
"""

import os
import sys
import time
import traceback
from datetime import datetime, timedelta

import parser as vacancy_parser

RUN_AT = os.environ.get("RUN_AT", "12:00")


def seconds_until_next_run() -> float:
    hh, mm = map(int, RUN_AT.split(":"))
    now = datetime.now()
    target = now.replace(hour=hh, minute=mm, second=0, microsecond=0)
    if target <= now:
        target += timedelta(days=1)
    return (target - now).total_seconds()


def main():
    print(f"Планировщик запущен. Ежедневный запуск в {RUN_AT} "
          f"(локальное время сервера, сейчас {datetime.now():%H:%M %Z}).")
    while True:
        wait = seconds_until_next_run()
        print(f"Следующий запуск через {wait/3600:.1f} ч.")
        time.sleep(wait)
        print(f"=== Запуск парсера: {datetime.now():%d.%m.%Y %H:%M} ===")
        try:
            vacancy_parser.main()
        except Exception:
            traceback.print_exc(file=sys.stderr)
        # небольшая пауза, чтобы не сработать дважды в одну минуту
        time.sleep(90)


if __name__ == "__main__":
    main()
