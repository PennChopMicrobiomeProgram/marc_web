# marc_web

A web interface for querying mARC

[![Tests](https://github.com/PennChopMicrobiomeProgram/marc_web/actions/workflows/pr.yml/badge.svg)](https://github.com/PennChopMicrobiomeProgram/marc_web/actions/workflows/pr.yml)
[![DockerHub](https://img.shields.io/docker/pulls/chopmicrobiome/marc_web)](https://hub.docker.com/repository/docker/chopmicrobiome/marc_web/)


## Dev

This is a Flask app with bootstrap, jquery, and datatables (via CDN). To start with local development:

```
git clone https://github.com/PennChopMicrobiomeProgram/marc_web.git
cd marc_web/
python -m venv env/
source env/bin/activate
pip install -r requirements.txt
pip install -r dev-requirements.txt

export MARC_DB_URL=sqlite:////path/to/marc_web/db.sqlite && export MARC_DB_LAST_SYNC=/path/to/last_sync && flask --app app/app run --debug
```

You'll need to create `/path/to/marc_web/db.sqlite` using [marc_db](https://github.com/PennChopMicrobiomeProgram/marc_db) and (optionally) `/path/to/last_sync` with a date/time stamp.

### Docker

To test the containerized version locally,

```
docker build -t chopmicrobiome/marc_web:dev -f Dockerfile .
docker run --rm -p 8080:80 -v /path/to/marc_web/:/data -e MARC_DB_URL='sqlite:////data/db.sqlite' chopmicrobiome/marc_web:dev
```

Use the full path to the `marc_web` repo where specified. Once this is running, you can navigate to `http://127.0.0.1:8080` in your browser and interact with it. The database it is using lives at `/path/to/marc_web/db.sqlite`.
