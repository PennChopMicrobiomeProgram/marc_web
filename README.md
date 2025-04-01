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

### Docker

To test the containerized version locally,

```
docker build -t myrepo/marc_web:dev -f Dockerfile .
docker run --rm -p 8080:80 -v /path/to/marc_web/:/data -e MARC_DB_URL='sqlite:////data/db.sqlite' myrepo/marc_web:dev
```

`myrepo` can be anything for local development. If you want to push anything to DockerHub it will have to be a repo you have proper permissions for. Use the full path to the `marc_web` repo where specified. Once this is running, you can navigate to `http://127.0.0.1:8080` in your browser and interact with it. The database it is using lives at `/path/to/marc_web/db.sqlite`.

### Deployment

There are a lot of options for deployment of containerized apps. If you have access to Kubernetes, it is the de facto standard for deploying containerized apps.