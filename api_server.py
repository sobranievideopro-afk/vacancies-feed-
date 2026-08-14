# -*- coding: utf-8 -*-
"""
REST API для портала «Кадровые резервы.РФ».
Отдаёт результаты парсера (vacancies.json) с фильтрами.

Запуск локально:   uvicorn api_server:app --reload
На Railway:        web-процесс из Procfile.

Эндпоинты:
  GET /health                     — проверка живости
  GET /api/vacancies              — все вакансии (объект с метаданными)
  GET /api/vacancies?city=Москва  — фильтр по городу
      &minSalary=500000           — только с раскрытой ЗП не ниже порога
      &source=hh.ru               — фильтр по источнику (подстрока)
      &q=CEO                      — поиск по названию/компании
      &limit=20&offset=0          — пагинация
  GET /api/cities                 — список городов со счётчиками
  GET /api/digest                 — дайджест в Markdown (text/plain)

CORS открыт для доменов из переменной окружения ALLOWED_ORIGINS
(через запятую), по умолчанию * — сузьте до домена портала в проде.
"""

import json
import os
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse

import config

app = FastAPI(title="Кадровые резервы — C-Level вакансии", version="1.0")

origins = [o.strip() for o in os.environ.get("ALLOWED_ORIGINS", "*").split(",")]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_methods=["GET"],
    allow_headers=["*"],
)


def load_data() -> dict:
    path = Path(config.OUTPUT_JSON)
    if not path.exists():
        raise HTTPException(503, "Данные ещё не собраны — дождитесь первого запуска парсера")
    return json.loads(path.read_text(encoding="utf-8"))


@app.get("/health")
def health():
    exists = Path(config.OUTPUT_JSON).exists()
    return {"status": "ok", "dataReady": exists}


@app.get("/api/vacancies")
def vacancies(
    city: str | None = None,
    minSalary: int = Query(0, ge=0),
    source: str | None = None,
    q: str | None = None,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    data = load_data()
    items = data["vacancies"]
    if city:
        items = [v for v in items if v.get("city", "").lower() == city.lower()]
    if minSalary > 0:
        items = [v for v in items if v.get("salaryLevel", 0) >= minSalary]
    if source:
        items = [v for v in items if source.lower() in v.get("source", "").lower()]
    if q:
        needle = q.lower()
        items = [v for v in items
                 if needle in v.get("title", "").lower()
                 or needle in v.get("company", "").lower()]
    total = len(items)
    return {
        "generatedAt": data["generatedAt"],
        "total": total,
        "limit": limit,
        "offset": offset,
        "items": items[offset:offset + limit],
    }


@app.get("/api/cities")
def cities():
    data = load_data()
    return {"generatedAt": data["generatedAt"], "cities": data.get("cities", {})}


@app.get("/api/digest", response_class=PlainTextResponse)
def digest():
    path = Path(config.OUTPUT_DIGEST)
    if not path.exists():
        raise HTTPException(503, "Дайджест ещё не сформирован")
    return path.read_text(encoding="utf-8")
