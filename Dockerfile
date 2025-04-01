FROM python:3.12-slim

# Need `git` to install `marc_db` as long as it's not on PyPi
RUN apt-get clean && apt-get -y update
RUN apt-get -y --no-install-recommends install curl git vim \
&& apt-get clean \
&& rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY . .

RUN pip install -r requirements.txt

# Until this faces third parties, it's easier to just provide debug info to users on crashes than have it just show a 500 error
ENV FLASK_DEBUG=1
ENV FLASK_APP=/app/app/app
ENV SQLALCHEMY_ECHO=True
ENV FLASK_RUN_HOST=0.0.0.0
ENV FLASK_RUN_PORT=80

EXPOSE 80

CMD [ "flask", "run" ]
