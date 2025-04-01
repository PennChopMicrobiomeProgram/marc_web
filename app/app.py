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
    return render_template("browse_isolates.html", isolates=get_isolates(db.session))


@app.route("/isolate/<isolate_id>")
def show_isolate(isolate_id):
    return render_template(
        "show_isolate.html", isolate=get_isolates(db.session, isolate_id)
    )


@app.route("/query", methods=["POST"])
def query():
    if request.method == "POST":
        query = request.form["query"]
        sql = text(query)
        with app.app_context():
            result = db.session.execute(sql).fetchall()
            return render_template(
                "view_query.html",
                query=query,
                columns=result[0]._fields,
                rows=[row._asdict().values() for row in result],
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
    """Health check endpoint."""
    try:
        with app.app_context():
            db.session.execute("SELECT 1")
        return {"status": "healthy"}, 200
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}, 500


@app.route("/info")
def info():
    return render_template(
        "info.html",
        version=__version__,
        marc_db_version=marc_db_version,
    )
