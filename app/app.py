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
from marc_db.views import (
    get_aliquots,
    get_assemblies,
    get_assembly_qc,
    get_isolates,
    get_taxonomic_assignments,
)
from pathlib import Path
from sqlalchemy import select, text, func
from sqlalchemy.pool import NullPool
from app.datatables import datatables_response, init_app, query_columns
from app.nl_query import generate_sql, generate_sql_modification
from werkzeug.middleware.proxy_fix import ProxyFix


app = Flask(__name__)
app.secret_key = os.urandom(12)

IS_DEV_SITE = os.environ.get("MARC_DEV", "").lower() == "true"


@app.context_processor
def inject_environment_flags():
    return {"is_dev_site": IS_DEV_SITE}


# This line is only used in production mode on a nginx server, follow instructions to setup forwarding for
# whatever production server you are using instead. It's ok to leave this in when running the dev server.
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

SQLALCHEMY_DATABASE_URI = os.environ["MARC_DB_URL"]
app.config["SQLALCHEMY_DATABASE_URI"] = SQLALCHEMY_DATABASE_URI
print(SQLALCHEMY_DATABASE_URI)
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "poolclass": NullPool,
    "connect_args": {"check_same_thread": False},
}
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
    init_app(db)


@app.route("/favicon.ico")
def favicon():
    return send_from_directory(
        Path(app.root_path) / "static",
        "favicon.ico",
        mimetype="image/vnd.microsoft.icon",
    )


@app.route("/")
def index():
    isolate_count = db.session.query(func.count(Isolate.sample_id)).scalar()
    patient_count = db.session.query(
        func.count(func.distinct(Isolate.subject_id))
    ).scalar()
    # Get counts of each unique special collection
    special_collections: dict[str, tuple[int, str]] = {}
    # Define description strings for known special collections
    special_collection_descriptions = {
        "Bacteremia": "Bacteria suspected to cause bacteremia",
        "Surveillance": "Bacteria isolated from the nares of patients as part of surveillance",
    }
    # Get counts of all special collections in a single query
    collection_counts = (
        db.session.query(Isolate.special_collection, func.count(Isolate.sample_id))
        .filter(Isolate.special_collection.is_not(None))
        .group_by(Isolate.special_collection)
        .all()
    )

    # Build the dictionary with counts and descriptions
    special_collections = {
        collection: (count, special_collection_descriptions.get(collection, ""))
        for collection, count in collection_counts
    }

    return render_template(
        "index.html",
        version=__version__,
        marc_db_version=marc_db_version,
        last_sync=get_db_last_sync(),
        isolate_count=isolate_count,
        patient_count=patient_count,
        special_collection_counts=special_collections,
    )


@app.route("/isolates")
def browse_isolates():
    return render_template("browse_isolates.html")


@app.route("/isolate-stats")
def isolate_stats():
    return render_template("isolate_stats.html")


@app.route("/api/isolates")
def api_isolates():
    return datatables_response(select(Isolate))


@app.route("/isolate/<isolate_id>")
def show_isolate(isolate_id):
    isolate_records = get_isolates(db.session, isolate_id)
    if not isolate_records or isolate_records[0] is None:
        return render_template("dne.html", isolate_id=isolate_id)
    isolate = isolate_records[0]
    assemblies = (
        db.session.query(Assembly)
        .filter(Assembly.isolate_id == isolate.sample_id)
        .order_by(Assembly.id)
        .all()
    )
    return render_template("show_isolate.html", isolate=isolate, assemblies=assemblies)


@app.route("/aliquots")
def browse_aliquots():
    return render_template("browse_aliquots.html")


@app.route("/api/aliquots")
def api_aliquots():
    return datatables_response(select(Aliquot))


@app.route("/aliquot/<aliquot_id>")
def show_aliquot(aliquot_id):
    aliquot = get_aliquots(db.session, aliquot_id)
    if not aliquot or aliquot[0] is None:
        return render_template("dne.html", aliquot_id=aliquot_id)
    return render_template("show_aliquot.html", aliquot=aliquot[0])


@app.route("/assemblies")
def browse_assemblies():
    return render_template("browse_assemblies.html")


@app.route("/api/assemblies")
def api_assemblies():
    query = select(
        Assembly.id,
        Assembly.isolate_id,
        Assembly.metagenomic_sample_id,
        Assembly.metagenomic_run_id,
        Assembly.nanopore_path.isnot(None).label("nanopore"),
        Assembly.run_number,
        Assembly.sunbeam_version,
        Assembly.sbx_sga_version,
        Assembly.ncbi_id,
    )
    return datatables_response(query)


@app.route("/api/assemblies/metrics")
def api_assembly_metrics():
    metrics = (
        db.session.query(
            Assembly.id.label("assembly_id"),
            Assembly.isolate_id.label("isolate_id"),
            AssemblyQC.contig_count,
            AssemblyQC.avg_contig_coverage,
            AssemblyQC.genome_size,
            AssemblyQC.completeness,
            AssemblyQC.contamination,
            Isolate.suspected_organism,
        )
        .join(AssemblyQC, Assembly.id == AssemblyQC.assembly_id)
        .outerjoin(Isolate, Assembly.isolate_id == Isolate.sample_id)
        .order_by(Assembly.id)
        .all()
    )

    return {
        "data": [
            {
                "assembly_id": m.assembly_id,
                "isolate_id": m.isolate_id,
                "contig_count": m.contig_count,
                "avg_contig_coverage": m.avg_contig_coverage,
                "genome_size": m.genome_size,
                "completeness": m.completeness,
                "contamination": m.contamination,
                "suspected_organism": m.suspected_organism,
            }
            for m in metrics
        ]
    }


@app.route("/assembly_qc")
def browse_assembly_qc():
    return render_template("browse_assembly_qc.html")


@app.route("/api/assembly_qc")
def api_assembly_qc():
    query = (
        select(
            AssemblyQC.assembly_id,
            Assembly.isolate_id.label("isolate_id"),
            AssemblyQC.contig_count,
            AssemblyQC.genome_size,
            AssemblyQC.n50,
            AssemblyQC.gc_content,
            AssemblyQC.cds,
            AssemblyQC.completeness,
            AssemblyQC.contamination,
            AssemblyQC.min_contig_coverage,
            AssemblyQC.avg_contig_coverage,
            AssemblyQC.max_contig_coverage,
        )
        .join(Assembly)
        .order_by(AssemblyQC.assembly_id)
    )
    return datatables_response(query)


@app.route("/assembly_qc/<int:assembly_id>")
def show_assembly_qc(assembly_id: int):
    qc_records = get_assembly_qc(db.session, assembly_id=assembly_id)
    if not qc_records or qc_records[0] is None:
        return render_template(
            "dne.html",
            message=f"No assembly QC record found for assembly {assembly_id}.",
        )
    qc_record = qc_records[0]
    qc, isolate_id = qc_record
    return render_template(
        "show_assembly_qc.html",
        assembly_qc=qc,
        assembly_id=assembly_id,
        isolate_id=isolate_id,
    )


@app.route("/taxonomic_assignments")
def browse_taxonomic_assignments():
    return render_template("browse_taxonomic_assignments.html")


@app.route("/api/taxonomic_assignments")
def api_taxonomic_assignments():
    query = (
        select(
            TaxonomicAssignment.assembly_id,
            Assembly.isolate_id.label("isolate_id"),
            TaxonomicAssignment.tool,
            TaxonomicAssignment.classification,
            TaxonomicAssignment.comment,
        )
        .join(Assembly)
        .order_by(TaxonomicAssignment.assembly_id)
    )
    return datatables_response(query)


@app.route("/taxonomic_assignments/<int:assembly_id>")
def show_taxonomic_assignment(assembly_id: int):
    assignments = get_taxonomic_assignments(db.session, assembly_id=assembly_id)
    if not assignments or assignments[0] is None:
        return render_template(
            "dne.html",
            message=f"No taxonomic assignment found for assembly {assembly_id}.",
        )
    assignment, isolate_id = assignments[0]
    return render_template(
        "show_taxonomic_assignment.html",
        assignment=assignment,
        assembly_id=assembly_id,
        isolate_id=isolate_id,
    )


@app.route("/antimicrobials")
def browse_antimicrobials():
    return render_template("browse_antimicrobials.html")


@app.route("/api/antimicrobials")
def api_antimicrobials():
    query = (
        select(
            Antimicrobial.id,
            Antimicrobial.assembly_id,
            Assembly.isolate_id.label("isolate_id"),
            Antimicrobial.contig_id,
            Antimicrobial.gene_symbol,
            Antimicrobial.gene_name,
            Antimicrobial.accession,
            Antimicrobial.element_type,
            Antimicrobial.resistance_product,
        )
        .join(Assembly)
        .order_by(Antimicrobial.id)
    )
    return datatables_response(query)


@app.route("/antimicrobial/<int:antimicrobial_id>")
def show_antimicrobial(antimicrobial_id: int):
    antimicrobial_record = (
        db.session.query(Antimicrobial, Assembly.isolate_id)
        .join(Assembly)
        .filter(Antimicrobial.id == antimicrobial_id)
        .first()
    )
    if not antimicrobial_record:
        return render_template("dne.html", antimicrobial_id=antimicrobial_id)
    antimicrobial_obj, isolate_id = antimicrobial_record
    return render_template(
        "show_antimicrobial.html",
        antimicrobial=antimicrobial_obj,
        isolate_id=isolate_id,
    )


@app.route("/assembly/<int:assembly_id>")
def show_assembly(assembly_id: int):
    assemblies = get_assemblies(db.session, id=assembly_id)
    if not assemblies or assemblies[0] is None:
        return render_template("dne.html", assembly_id=assembly_id)
    assembly = assemblies[0]
    qc = assembly.assembly_qc
    assignments = (
        list(assembly.taxonomic_assignments) if assembly.taxonomic_assignments else []
    )
    antimicrobials = list(assembly.antimicrobials) if assembly.antimicrobials else []
    contaminants = list(assembly.contaminants) if assembly.contaminants else []
    return render_template(
        "show_assembly.html",
        assembly=assembly,
        qc=qc,
        assignments=assignments,
        antimicrobials=antimicrobials,
        contaminants=contaminants,
    )


@app.route("/query", methods=["GET", "POST"])
def query():
    """Render the query form and determine column names for the SQL."""
    query_str = request.form.get("query", "") if request.method == "POST" else ""
    columns = []
    error = None
    if query_str:
        try:
            columns = query_columns(query_str)
        except Exception as e:
            error = str(e)
    return render_template(
        "query.html",
        query=query_str,
        columns=columns,
        models=MARC_MODELS,
        model_fields=MARC_MODEL_FIELDS,
        error=error,
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


@app.route("/api/query", methods=["POST"])
def api_query():
    """Return results for a custom SQL query in DataTables format."""
    query = request.form.get("query")
    if not query:
        return {"error": "No query provided"}, 400
    try:
        return datatables_response(query)
    except Exception as e:
        print(f"Error executing query: {e}")  # Log the full error server-side
        return {"error": "Query execution failed"}, 500


@app.route("/api/nl_query", methods=["POST"])
def api_nl_query():
    """Translate a natural language question into SQL and execute it."""
    question = request.form.get("prompt")
    starting_query = request.form.get("query")

    if not question:
        return {"error": "No query provided"}, 400

    if not starting_query:
        try:
            return generate_sql(question), 200
        except Exception as e:
            print(f"Error creating NL query: {e}")
            return {"error": "Query generation failed"}, 500
    else:
        try:
            return generate_sql_modification(question, starting_query), 200
        except Exception as e:
            print(f"Error creating NL query with starting query: {e}")
            return {"error": "Query modification failed"}, 500


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


@app.route("/reset_db_connections")
def reset_db_connections():
    try:
        db.engine.dispose()
        return {"status": "db_conns_reset"}, 200
    except Exception as e:
        return {"status": "db_conns_not_reset", "error": str(e)}, 500


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
