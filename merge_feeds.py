# -*- coding: utf-8 -*-
"""Склейка внешнего фида (vacancies_external.json из GitHub) с локальным
файлом hh+Telegram (vacancies_hh_tg.json) в общий vacancies_all.json.
Дедупликация по URL, единая сортировка: раскрытая зарплата и её верхняя
граница -> масштаб ответственности."""
import json
from datetime import datetime, timezone
from pathlib import Path

def load(path):
    p = Path(path)
    if not p.exists():
        return []
    d = json.loads(p.read_text(encoding="utf-8"))
    return d["vacancies"] if isinstance(d, dict) else d

merged, seen = [], set()
for src in ("vacancies_external.json", "vacancies_hh_tg.json"):
    for v in load(src):
        key = v.get("url", "").split("?")[0].lower()
        if key and key not in seen:
            seen.add(key)
            merged.append(v)

merged.sort(key=lambda v: (v.get("salaryLevel", 0) > 0, v.get("salaryLevel", 0),
                           v.get("scopeScore", 0)), reverse=True)
cities = {}
for v in merged:
    cities[v.get("city", "Другое")] = cities.get(v.get("city", "Другое"), 0) + 1

Path("vacancies_all.json").write_text(json.dumps({
    "generatedAt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    "total": len(merged), "cities": cities, "vacancies": merged,
}, ensure_ascii=False, indent=2), encoding="utf-8")
