import csv
import os
from app import __version__, get_db_last_sync
from flask import (
    Flask,
    make_response,
    redirect,
    render_template,
    request,
    send_from_directory,
)
from flask_sqlalchemy import SQLAlchemy
from io import StringIO
from marc_db import __version__ as marc_db_version
from marc_db.models import (
    Aliquot,
    Assembly,
    AssemblyQC,
    TaxonomicAssignment,
    Antimicrobial,
    Base,
    Isolate,
)
from marc_db.views import get_aliquots, get_isolates
from pathlib import Path
from sqlalchemy import text, func, or_, cast, String
from werkzeug.middleware.proxy_fix import ProxyFix


app = Flask(__name__)
app.secret_key = os.urandom(12)

# This line is only used in production mode on a nginx server, follow instructions to setup forwarding for
# whatever production server you are using instead. It's ok to leave this in when running the dev server.
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

SQLALCHEMY_DATABASE_URI = os.environ["MARC_DB_URL"]
app.config["SQLALCHEMY_DATABASE_URI"] = SQLALCHEMY_DATABASE_URI
print(SQLALCHEMY_DATABASE_URI)
db = SQLAlchemy(model_class=Base)
db.init_app(app)

# List of all available models for the query page
MARC_MODELS = [
    Aliquot,
    Isolate,
    Assembly,
    AssemblyQC,
    TaxonomicAssignment,
    Antimicrobial,
]

# Mapping of model table names to their field names
MARC_MODEL_FIELDS = {
    m.__table__.name: [c.name for c in m.__table__.columns] for m in MARC_MODELS
}

with app.app_context():
    db.create_all()


def datatables_response(model):
    """Return model rows formatted for DataTables server-side processing."""
    columns = list(model.__table__.columns.keys())

    query = db.session.query(model)

    total_records = query.count()

    search_value = request.args.get("search[value]")
    if search_value:
        filters = [
            cast(getattr(model, c), String).ilike(f"%{search_value}%") for c in columns
        ]
        query = query.filter(or_(*filters))

    for idx, col in enumerate(columns):
        val = request.args.get(f"columns[{idx}][search][value]")
        if val:
            query = query.filter(cast(getattr(model, col), String).ilike(f"%{val}%"))

    order_idx = request.args.get("order[0][column]")
    if order_idx is not None:
        col_name = columns[int(order_idx)]
        col = getattr(model, col_name)
        if request.args.get("order[0][dir]", "asc") == "desc":
            col = col.desc()
        query = query.order_by(col)

    records_filtered = query.count()

    start = request.args.get("start", 0, type=int)
    length = request.args.get("length", 20, type=int)
    rows = query.offset(start).limit(length).all()

    data = [{c: getattr(r, c) for c in columns} for r in rows]

    return {
        "draw": int(request.args.get("draw", 1)),
        "recordsTotal": total_records,
        "recordsFiltered": records_filtered,
        "data": data,
    }


@app.route("/favicon.ico")
def favicon():
    return send_from_directory(
        Path(app.root_path) / "static",
        "favicon.ico",
        mimetype="image/vnd.microsoft.icon",
    )


@app.route("/")
def index():
    return render_template(
        "index.html",
        version=__version__,
        marc_db_version=marc_db_version,
        last_sync=get_db_last_sync(),
    )


@app.route("/isolates")
def browse_isolates():
    return render_template("browse_isolates.html")


@app.route("/api/isolates")
def api_isolates():
    return datatables_response(Isolate)


@app.route("/isolate/<isolate_id>")
def show_isolate(isolate_id):
    isolate = get_isolates(db.session, isolate_id)
    if not isolate:
        return render_template("dne.html", isolate_id=isolate_id)
    return render_template("show_isolate.html", isolate=isolate[0])


@app.route("/aliquots")
def browse_aliquots():
    return render_template("browse_aliquots.html")


@app.route("/api/aliquots")
def api_aliquots():
    return datatables_response(Aliquot)


@app.route("/aliquot/<aliquot_id>")
def show_aliquot(aliquot_id):
    aliquot = get_aliquots(db.session, aliquot_id)
    if not aliquot:
        return render_template("dne.html", aliquot_id=aliquot_id)
    return render_template("show_aliquot.html", aliquot=aliquot[0])


@app.route("/query", methods=["GET", "POST"])
def query():
    if request.method == "GET":
        return render_template(
            "query.html",
            query="",
            columns=[],
            rows=[],
            models=MARC_MODELS,
            model_fields=MARC_MODEL_FIELDS,
        )
    elif request.method == "POST":
        query = request.form["query"]

        try:
            sql = text(query)
            with app.app_context():
                result = db.session.execute(sql).fetchall()
        except Exception as e:
            return render_template(
                "query.html",
                query=query,
                columns=[],
                rows=[],
                models=MARC_MODELS,
                model_fields=MARC_MODEL_FIELDS,
                error=str(e),
            )

        if not result:
            return render_template(
                "query.html",
                query=query,
                columns=[],
                rows=[],
                models=MARC_MODELS,
                model_fields=MARC_MODEL_FIELDS,
                error="No results found.",
            )

        return render_template(
            "query.html",
            query=query,
            columns=result[0]._fields,
            rows=[row._asdict().values() for row in result],
            models=MARC_MODELS,
            model_fields=MARC_MODEL_FIELDS,
        )


@app.route("/download", methods=["POST"])
def download():
    if request.method == "POST":
        query = request.form["query"]
        sql = text(query)
        with app.app_context():
            result = db.session.execute(sql).fetchall()
            columns = result[0]._fields
            rows = [row._asdict().values() for row in result]

            csv_file = StringIO()
            writer = csv.writer(csv_file)
            writer.writerow(columns)
            for row in rows:
                writer.writerow(row)

            # Create the response and set the appropriate headers
            response = make_response(csv_file.getvalue())
            response.headers["Content-Disposition"] = (
                f"attachment; filename=marc_query_download.csv"
            )
            response.headers["Content-type"] = "text/csv"
            return response

    return redirect("/")


@app.route("/api", methods=["POST"])
def api():
    try:
        if request.method == "POST":
            query = request.form["query"]
            sql = text(query)
            with app.app_context():
                result = db.session.execute(sql).fetchall()
                return {"result": [dict(row) for row in result], "status_code": 200}

        return {"result": ["No query provided"], "status_code": 400}
    except Exception as e:
        return {"result": [str(e)], "status_code": 500}


@app.route("/health")
def health():
    try:
        db.session.execute(text("SELECT 1")).scalar()
        return {"status": "ready"}, 200
    except Exception as e:
        return {"status": "unready", "error": str(e)}, 500


@app.route("/liveness")
def liveness():
    """Liveness check endpoint."""
    return {"status": "alive"}, 200


@app.route("/info")
def info():
    return render_template(
        "info.html",
        version=__version__,
        marc_db_version=marc_db_version,
    )


@app.route("/arch")
def arch():
    return render_template("arch.html")


if not app.debug:

    @app.errorhandler(404)
    def page_not_found(e):
        return render_template("dne.html"), 404

    @app.errorhandler(500)
    @app.errorhandler(Exception)
    def internal_server_error(e):
        # Figure out best method for alert on error
        # This should probably contact someone to let them know something went wrong
        print(f"Internal Server Error: {e}")
        return (
            render_template(
                "dne.html",
                message="Sorry! Something went wrong on our end. We've been notified and are working to fix it.",
            ),
            500,
        )
