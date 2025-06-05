import csv
import os
from app import __version__
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
from marc_db.models import Aliquot, Base, Isolate
from marc_db.views import get_aliquots, get_isolates
from pathlib import Path
from sqlalchemy import text
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

with app.app_context():
    db.create_all()


@app.route("/favicon.ico")
def favicon():
    return send_from_directory(
        Path(app.root_path) / "static",
        "favicon.ico",
        mimetype="image/vnd.microsoft.icon",
    )


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/isolates")
def browse_isolates():
    return render_template("browse_isolates.html", isolates=get_isolates(db.session))


@app.route("/isolate/<isolate_id>")
def show_isolate(isolate_id):
    return render_template(
        "show_isolate.html", isolate=get_isolates(db.session, isolate_id)
    )


@app.route("/aliquots")
def browse_aliquots():
    return render_template("browse_aliquots.html", aliquots=get_aliquots(db.session))


@app.route("/aliquot/<aliquot_id>")
def show_aliquot(aliquot_id):
    return render_template(
        "show_aliquot.html", aliquot=get_aliquots(db.session, aliquot_id)
    )


@app.route("/query", methods=["GET", "POST"])
def query():
    if request.method == "GET":
        return render_template(
            "query.html",
            query="",
            columns=[],
            rows=[],
            models=[Aliquot, Isolate],
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
                models=[Aliquot, Isolate],
                error=str(e),
            )

        if not result:
            return render_template(
                "query.html",
                query=query,
                columns=[],
                rows=[],
                models=[Aliquot, Isolate],
                error="No results found.",
            )

        return render_template(
            "query.html",
            query=query,
            columns=result[0]._fields,
            rows=[row._asdict().values() for row in result],
            models=[Aliquot, Isolate],
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
