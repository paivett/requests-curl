FROM python:3.8

RUN pip install pipenv

ENV PYCURL_SSL_LIBRARY=openssl

RUN apt-get update && apt-get install libcurl4-openssl-dev libssl-dev

WORKDIR /code

COPY Pipfile ./

RUN pipenv install --dev

COPY requests_curl requests_curl

COPY tests_e2e tests_e2e
