import requests

from requests_curl import CURLAdapter

from tests_e2e import HTTP_BIN_BASE_URL


def test_empty_cookies_when_no_cookies_were_set():
    session = requests.Session()

    session.mount("http://", CURLAdapter())

    url = f"{HTTP_BIN_BASE_URL}/cookies"

    response = session.get(url)

    assert not response.cookies


def test_set_single_cookie():
    session = requests.Session()

    session.mount("http://", CURLAdapter())

    url = f"{HTTP_BIN_BASE_URL}/cookies/set/foo/cookievalue"

    response = session.get(url)

    assert session.cookies["foo"] == "cookievalue"

    cookies = response.json()["cookies"]
    assert cookies == {"foo": "cookievalue"}


def test_delete_cookies():
    session = requests.Session()

    session.mount("http://", CURLAdapter())

    url = f"{HTTP_BIN_BASE_URL}/cookies/set/foo/cookievalue"

    response = session.get(url)

    assert session.cookies["foo"] == "cookievalue"

    session.cookies.clear()

    response = session.get(f"{HTTP_BIN_BASE_URL}/cookies")

    assert response.json()["cookies"] == {}
