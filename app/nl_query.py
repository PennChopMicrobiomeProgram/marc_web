"""Utility functions for natural language to SQL queries."""

from typing import Dict, List

from sqlalchemy import text
from sqlalchemy.orm import Session


def _to_sql(question: str) -> str:
    """Naively convert a natural language question to SQL.

    This is a placeholder implementation meant to demonstrate how the
    translation could be structured. Only a very small set of questions is
    supported.
    """

    q = question.lower()
    if "how many isolates" in q:
        return "SELECT COUNT(*) AS count FROM isolates"
    raise ValueError("Unsupported question")


def run_nl_query(session: Session, question: str) -> Dict[str, List[Dict[str, int]]]:
    """Execute a natural language query against the database."""

    sql = _to_sql(question)
    result = session.execute(text(sql)).fetchall()
    return {"sql": sql, "result": [dict(row._mapping) for row in result]}
