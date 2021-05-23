import requests
from requests.auth import HTTPBasicAuth
from requests_curl.adapter import CURLAdapter

from tests_e2e import HTTP_BIN_BASE_URL


def test_successful_basic_auth():
    session = requests.Session()

    session.mount("http://", CURLAdapter())

    user = "someuser"
    pwd = "somepwd"

    url = f"{HTTP_BIN_BASE_URL}/basic-auth/{user}/{pwd}"

    response = session.get(url, auth=HTTPBasicAuth(user, pwd))

    assert response.status_code == 200


def test_unauthorized_basic_auth():
    session = requests.Session()

    session.mount("http://", CURLAdapter())

    user = "someuser"
    pwd = "somepwd"

    url = f"{HTTP_BIN_BASE_URL}/basic-auth/{user}/{pwd}"

    response = session.get(url)

    assert response.status_code == 401


def test_successful_bearer_token_auth():
    session = requests.Session()

    session.mount("http://", CURLAdapter())

    token = "sometoken"

    url = f"{HTTP_BIN_BASE_URL}/bearer"

    headers = {"Authorization": f"Bearer {token}"}

    response = session.get(url, headers=headers)

    assert response.status_code == 200
    assert response.json()["token"] == token


def test_unauthorized_bearer_token_auth():
    session = requests.Session()

    session.mount("http://", CURLAdapter())

    url = f"{HTTP_BIN_BASE_URL}/bearer"

    response = session.get(url)

    assert response.status_code == 401
