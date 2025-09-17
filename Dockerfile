FROM python:3.13-slim

# Need `git` to install `marc_db` as long as it's not on PyPi
RUN apt-get clean && apt-get -y update
RUN apt-get -y --no-install-recommends install curl git vim \
&& apt-get clean \
&& rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY . .

RUN pip install -r requirements.txt

ENV FLASK_DEBUG=0
ENV FLASK_APP=/app/app/app
ENV SQLALCHEMY_ECHO=False
ENV FLASK_RUN_HOST=0.0.0.0
ENV FLASK_RUN_PORT=80

EXPOSE 80

CMD [ "flask", "run" ]
