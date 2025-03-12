import os
from flask import Flask, redirect, render_template, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from marc_db.models import Aliquot, Base, Isolate
from marc_db.views import get_aliquots, get_isolates
from pathlib import Path
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
    return render_template("isolate.html", isolate=get_isolates(db.session, isolate_id))
