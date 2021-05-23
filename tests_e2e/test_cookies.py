import requests

from requests_curl import CURLAdapter


def test_empty_cookies_when_no_cookies_were_set():
    session = requests.Session()

    session.mount("http://", CURLAdapter())

    url = f"http://http_bin/cookies"

    response = session.get(url)

    assert not response.cookies


def test_set_single_cookie():
    session = requests.Session()

    session.mount("http://", CURLAdapter())

    url = "http://http_bin/cookies/set/foo/cookievalue"

    response = session.get(url)

    assert session.cookies["foo"] == "cookievalue"

    cookies = response.json()["cookies"]
    assert cookies == {"foo": "cookievalue"}


def test_delete_cookies():
    session = requests.Session()

    session.mount("http://", CURLAdapter())

    url = "http://http_bin/cookies/set/foo/cookievalue"

    response = session.get(url)

    assert session.cookies["foo"] == "cookievalue"

    session.cookies.clear()

    response = session.get("http://http_bin/cookies")

    assert response.json()["cookies"] == {}
