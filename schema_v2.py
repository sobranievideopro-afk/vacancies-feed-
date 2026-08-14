# -*- coding: utf-8 -*-
"""Схема v2 карточки вакансии «Кадровые резервы.РФ».
build_card(flat) превращает плоскую запись парсера в полную карточку.
Незаполнимые из публичных источников поля остаются null —
они предназначены для последующего обогащения."""
import hashlib
import re
from datetime import datetime, timezone

EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")
PHONE_RE = re.compile(r"(?:\+7|8)[\s(]*\d{3}[\s)]*\d{3}[\s-]*\d{2}[\s-]*\d{2}")
TEAM_RE = re.compile(r"(?:команд\w*|подчинени\w*|департамент\w*)\D{0,20}(\d{1,4})\s*(?:\+)?\s*(?:человек|сотрудник|чел\b)", re.I)
EXP_RE = re.compile(r"опыт\D{0,30}(\d{1,2})\s*(?:лет|год)", re.I)

LEVEL_BY_SCOPE = {3: "C-level (первое лицо)", 2: "C-level / директор функции", 1: "VP / Head", 0: "руководитель"}

def _detect(patterns, text):
    return next((label for label, pat in patterns if re.search(pat, text, re.I)), None)

def _salary(flat):
    text = flat.get("salaryText", "") or ""
    level = flat.get("salaryLevel", 0) or 0
    disclosed = level > 0
    nums = [int(re.sub(r"\D", "", n)) for n in re.findall(r"\d[\d\s\u00a0]{3,12}", text)] if disclosed else []
    cur = "EUR" if "€" in text else "USD" if "$" in text else "RUB"
    gross = None
    if re.search(r"на руки|net", text, re.I): gross = False
    elif re.search(r"до вычета|gross", text, re.I): gross = True
    return {"from": nums[0] if nums else None,
            "to": (nums[1] if len(nums) > 1 else nums[0]) if nums else None,
            "currency": cur if disclosed else None, "gross": gross,
            "disclosed": disclosed, "text": text, "levelRub": level}

def build_card(flat: dict) -> dict:
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    url = flat.get("url", "")
    blob = " ".join(str(flat.get(k, "")) for k in ("title", "summary", "location", "salaryText"))
    uid = hashlib.md5(url.split("?")[0].lower().encode()).hexdigest()[:16]
    source = flat.get("source", "")
    portal = ("rabota.ru" if "rabota" in source else "career.habr.com" if "habr" in source
              else "linkedin.com" if "linkedin" in source else source or "unknown")
    m_id = re.search(r"/(?:vacancy|vacancies|view)/[^/]*?(\d{6,})", url)
    team = TEAM_RE.search(blob); exp = EXP_RE.search(blob)
    email = EMAIL_RE.search(blob); phone = PHONE_RE.search(blob)
    work_format = _detect([("удалённо", r"удал[её]нн|remote"), ("гибрид", r"гибрид|hybrid"),
                           ("офис", r"офис|on-?site|м\.\s")], blob)
    employment = _detect([("проектная", r"проектн|разов|внештат"), ("частичная", r"частичн|part-?time"),
                          ("полная", r"полн\w+ (?:рабочий день|занятост)|full-?time")], blob) or "полная"
    conf = {"title": 1.0, "salary": 1.0 if flat.get("salaryLevel", 0) else 0.9,
            "city": 1.0 if flat.get("city") not in (None, "", "Другое") else 0.4,
            "workFormat": 0.7 if work_format else 0.0,
            "employmentType": 0.7 if employment != "полная" else 0.5,
            "teamSize": 0.8 if team else 0.0}
    return {
        "id": uid, "portal": portal, "url": url, "sourceVacancyId": m_id.group(1) if m_id else None,
        "basic": {
            "title": flat.get("title"), "company": flat.get("company") or None,
            "companyDescription": None, "city": flat.get("city"),
            "region": flat.get("location") or None, "workFormat": work_format,
            "employmentType": employment, "salary": _salary(flat),
            "description": flat.get("summary"), "requirements": None, "conditions": None,
            "publishedAt": flat.get("published") or None,
            "applyContact": (email.group(0) if email else None) or (phone.group(0) if phone else None),
        },
        "profile": {
            "function": None, "industry": None,
            "positionLevel": LEVEL_BY_SCOPE.get(flat.get("scopeScore", 0), "руководитель"),
            "totalExperienceYears": int(exp.group(1)) if exp else None,
            "managementExperienceYears": None, "skills": [], "competencies": [],
            "mustHave": [], "niceToHave": [], "education": None, "languages": [],
            "certificates": [], "industryExperience": [],
            "teamManagement": bool(team) or None,
            "teamSize": int(team.group(1)) if team else None, "responsibilityScope": None,
        },
        "role": {k: None for k in ("purpose", "expectedResults", "kpi", "responsibilityZone",
                 "reportsTo", "hasDirectReports", "openingReason", "companyStage",
                 "businessChallenges", "probationPeriod", "first90DaysPlan")} | {"tasks": []},
        "terms": {k: None for k in ("schedule", "officeAddress", "businessTrips", "relocation",
                 "relocationPackage", "bonusSize", "compensationStructure", "dms",
                 "corporateEducation", "equipment", "vacation")} | {"benefits": []},
        "apply": {"contactPerson": None, "email": email.group(0) if email else None,
                  "phone": phone.group(0) if phone else None, "externalApplyUrl": url,
                  "inPlatformApply": False, "coverLetterRequired": None,
                  "screeningQuestions": [], "selectionStages": [], "deadline": None},
        "meta": {"firstSeenAt": flat.get("collectedAt", now), "lastCheckedAt": now,
                 "sourceUpdatedAt": None,
                 "status": "active" if flat.get("verified") else "unverified",
                 "language": "ru", "summary": flat.get("summary"),
                 "extractedAt": now, "extractionMethod": "public-page-parse",
                 "confidence": conf, "possibleDuplicate": False, "duplicateUrls": []},
        "companyLogo": {"url": flat.get("companyLogoUrl"), "file": None,
                        "sourceUrl": flat.get("companyLogoSourceUrl"),
                        "alt": flat.get("company") or None,
                        "format": (flat.get("companyLogoUrl") or "").rsplit(".", 1)[-1].upper()
                                  if flat.get("companyLogoUrl") else None,
                        "updatedAt": now if flat.get("companyLogoUrl") else None,
                        "verified": flat.get("companyLogoVerified", False)},
    }
