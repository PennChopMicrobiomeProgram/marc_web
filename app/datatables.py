# Utility functions for DataTables responses
from flask import request
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text, func, or_, cast, String, select
from sqlalchemy.exc import OperationalError, ProgrammingError
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
    values = request.values

    def empty_response(columns):
        return {
            "draw": int(values.get("draw", 1)),
            "recordsTotal": 0,
            "recordsFiltered": 0,
            "data": [],
            "columns": list(columns),
        }

    if isinstance(query, str):
        base_sql = query.rstrip(";")
        start = values.get("start", 0, type=int)
        length = values.get("length", 20, type=int)

        try:
            columns = query_columns(query)
        except (OperationalError, ProgrammingError):
            return empty_response([])

        quoted_cols = [f'"{c}"' for c in columns]

        search_value = values.get("search[value]")
        params = {}
        filters = []

        dialect = db.engine.dialect.name
        if search_value:
            like_op = "ILIKE" if dialect == "postgresql" else "LIKE"
            like = (
                f"%{search_value.lower()}%"
                if like_op == "LIKE"
                else f"%{search_value}%"
            )
            params["search"] = like
            exprs = []
            for c in quoted_cols:
                col_expr = f"CAST(q.{c} AS TEXT)"
                if like_op == "LIKE":
                    col_expr = f"LOWER({col_expr})"
                exprs.append(f"{col_expr} {like_op} :search")
            filters.append("(" + " OR ".join(exprs) + ")")

        for idx, col in enumerate(columns):
            val = values.get(f"columns[{idx}][search][value]")
            if val:
                like_op = "ILIKE" if dialect == "postgresql" else "LIKE"
                like = f"%{val.lower()}%" if like_op == "LIKE" else f"%{val}%"
                params[f"col_{idx}"] = like
                col_expr = f'CAST(q."{col}" AS TEXT)'
                if like_op == "LIKE":
                    col_expr = f"LOWER({col_expr})"
                filters.append(f"{col_expr} {like_op} :col_{idx}")

        base_select = f"SELECT * FROM ({base_sql}) AS q"
        try:
            total_records = db.session.scalar(
                text(f"SELECT COUNT(*) FROM ({base_sql}) AS q")
            )

            filtered_sql = base_select
            if filters:
                filtered_sql += " WHERE " + " AND ".join(filters)

            records_filtered = db.session.scalar(
                text(f"SELECT COUNT(*) FROM ({filtered_sql}) AS sq"),
                params,
            )

            order_idx = values.get("order[0][column]", type=int)
            if order_idx is not None and 0 <= order_idx < len(columns):
                col = columns[order_idx]
                direction = (
                    "DESC" if values.get("order[0][dir]", "asc") == "desc" else "ASC"
                )
                filtered_sql += f' ORDER BY "{col}" {direction}'

            paginated_sql = filtered_sql + " LIMIT :limit OFFSET :offset"
            params.update({"limit": length, "offset": start})

            rows = db.session.execute(text(paginated_sql), params).mappings().all()
        except (OperationalError, ProgrammingError):
            return empty_response(columns)

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

    # Ensure ORM selections return column mappings instead of model objects
    columns = [c.key for c in query.selected_columns]
    base_query = query.with_only_columns(query.selected_columns)
    try:
        total_records = _execute_count(base_query)

        search_value = values.get("search[value]")
        if search_value:
            filters = [
                cast(c, String).ilike(f"%{search_value}%")
                for c in query.selected_columns
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
    except (OperationalError, ProgrammingError):
        return empty_response(columns)

    data = [dict(r._mapping) for r in rows]

    return {
        "draw": int(values.get("draw", 1)),
        "recordsTotal": total_records,
        "recordsFiltered": records_filtered,
        "data": data,
        "columns": columns,
    }
