FROM python:3.13-slim

# Need `git` to install `marc_db` as long as it's not on PyPi
RUN apt-get clean && apt-get -y update
RUN apt-get -y --no-install-recommends install curl git vim \
&& apt-get clean \
&& rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY . .

RUN pip install -r requirements.txt

EXPOSE 80

CMD ["gunicorn", "--bind", "0.0.0.0:80", "--workers", "2", "--threads", "2", "--timeout", "120", "--max-requests", "1000", "--max-requests-jitter", "100", "--preload", "app.app:app"]
