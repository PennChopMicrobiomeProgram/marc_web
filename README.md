# marc_web
A web interface for querying mARC


## Dev

This is a Flask app with bootstrap, jquery, and datatables (via CDN). To start with local development:

```
git clone https://github.com/PennChopMicrobiomeProgram/marc_web.git
cd marc_web/
python -m venv env/
source env/bin/activate
pip install -r requirements.txt
pip install -r dev-requirements.txt

export MARC_DB_URL=sqlite:////path/to/marc_web/db.sqlite && export FLASK_DEBUG=1 && flask --app app/app run
```

You'll need to create `/path/to/marc_web/db.sqlite` using [marc_db](https://github.com/PennChopMicrobiomeProgram/marc_db).