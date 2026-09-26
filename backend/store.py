"""SQLite store: cases (full JSON), reviews, audit log. OWNER: Yadnesh."""
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from backend.schemas import AnalysisResult, CaseSummary, Review

DB = Path(__file__).parent / "store" / "unmask.db"


def _conn() -> sqlite3.Connection:
    DB.parent.mkdir(exist_ok=True)
    c = sqlite3.connect(DB)
    c.execute("create table if not exists cases(id text primary key, created_at text, json text)")
    c.execute("create table if not exists audit(id integer primary key autoincrement,"
              " case_id text, at text, action text, detail text)")
    return c


def _log(c, case_id: str, at: str, action: str, detail: str) -> None:
    c.execute("insert into audit(case_id,at,action,detail) values(?,?,?,?)", (case_id, at, action, detail))


def save(r: AnalysisResult) -> None:
    with _conn() as c:
        c.execute("insert or replace into cases values(?,?,?)", (r.case_id, r.created_at, r.model_dump_json()))
        _log(c, r.case_id, r.created_at, "analyzed", r.band)


def get(case_id: str) -> AnalysisResult | None:
    with _conn() as c:
        row = c.execute("select json from cases where id=?", (case_id,)).fetchone()
    return AnalysisResult.model_validate_json(row[0]) if row else None


def list_cases() -> list[CaseSummary]:
    with _conn() as c:
        rows = c.execute("select json from cases order by created_at desc").fetchall()
    return [CaseSummary.model_validate_json(r[0]) for r in rows]


def review(case_id: str, decision: str, note: str) -> AnalysisResult | None:
    r = get(case_id)
    if not r:
        return None
    r.review = Review(decision=decision, note=note, at=datetime.now(timezone.utc).isoformat())
    with _conn() as c:
        c.execute("update cases set json=? where id=?", (r.model_dump_json(), case_id))
        _log(c, case_id, r.review.at, decision, note)
    return r


def audit(case_id: str | None = None) -> list[dict]:
    q = "select case_id,at,action,detail from audit" + (" where case_id=?" if case_id else "") + " order by id desc"
    with _conn() as c:
        rows = c.execute(q, (case_id,) if case_id else ()).fetchall()
    return [dict(zip(["case_id", "at", "action", "detail"], r)) for r in rows]
