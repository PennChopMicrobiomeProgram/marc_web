# Utility functions for DataTables responses
from flask import request
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text, func, or_, cast, String, select
from sqlalchemy.sql import Select

# `db` will be provided by the application using this module.
db: SQLAlchemy


def init_app(database: SQLAlchemy) -> None:
    """Set the globally used SQLAlchemy database instance."""
    global db
    db = database


def _execute_count(q):
    return db.session.scalar(select(func.count()).select_from(q.subquery()))


def query_columns(query):
    """Return column names for a query without fetching data."""
    if isinstance(query, Select):
        return [c.key for c in query.selected_columns]
    if isinstance(query, str):
        limited_sql = f"SELECT * FROM ({query.rstrip(';')}) AS q LIMIT 0"
        result = db.session.execute(text(limited_sql))
        return list(result.keys())
    raise TypeError("query must be a SQLAlchemy Select or SQL string")


def datatables_response(query):
    """Return query results formatted for DataTables server-side processing.

    Parameters
    ----------
    query: sqlalchemy.sql.Select | str
        Query to execute. May be a SQLAlchemy Select object or a raw SQL string.
    """
    if isinstance(query, str):
        base_sql = query.rstrip(";")
        values = request.values
        start = values.get("start", 0, type=int)
        length = values.get("length", 20, type=int)
        count_sql = f"SELECT COUNT(*) FROM ({base_sql}) AS q"
        total_records = db.session.scalar(text(count_sql))
        records_filtered = total_records
        paginated_sql = f"{base_sql} LIMIT :limit OFFSET :offset"
        rows = (
            db.session.execute(text(paginated_sql), {"limit": length, "offset": start})
            .mappings()
            .all()
        )
        columns = query_columns(query)
        data = [dict(r) for r in rows]
        return {
            "draw": int(values.get("draw", 1)),
            "recordsTotal": total_records,
            "recordsFiltered": records_filtered,
            "data": data,
            "columns": list(columns),
        }

    if not isinstance(query, Select):
        raise TypeError("query must be a SQLAlchemy Select, Query, or SQL string")

    columns = [c.key for c in query.selected_columns]
    base_query = query
    total_records = _execute_count(base_query)

    values = request.values
    search_value = values.get("search[value]")
    if search_value:
        filters = [
            cast(c, String).ilike(f"%{search_value}%") for c in query.selected_columns
        ]
        base_query = base_query.where(or_(*filters))

    for idx, col in enumerate(query.selected_columns):
        val = values.get(f"columns[{idx}][search][value]")
        if val:
            base_query = base_query.where(cast(col, String).ilike(f"%{val}%"))

    order_idx = values.get("order[0][column]")
    if order_idx is not None:
        col = query.selected_columns[int(order_idx)]
        if values.get("order[0][dir]", "asc") == "desc":
            col = col.desc()
        base_query = base_query.order_by(col)

    records_filtered = _execute_count(base_query)

    start = values.get("start", 0, type=int)
    length = values.get("length", 20, type=int)
    paginated = base_query.offset(start).limit(length)
    rows = db.session.execute(paginated).all()
    data = [dict(r._mapping) for r in rows]

    return {
        "draw": int(values.get("draw", 1)),
        "recordsTotal": total_records,
        "recordsFiltered": records_filtered,
        "data": data,
        "columns": columns,
    }
