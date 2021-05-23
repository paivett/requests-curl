import requests

from requests_curl.adapter import CURLAdapter

from tests_e2e import HTTP_BIN_BASE_URL


def test_headers():
    session = requests.Session()

    session.mount("http://", CURLAdapter())

    url = f"{HTTP_BIN_BASE_URL}/headers"

    headers_to_send = {
        "User-Agent": "my-app/0.0.1",
        "Dnt": "1",
        "Accept-Language": "en-US",
        "Cache-Control": "no-cache",
        "Date": "Tue, 15 Nov 1994 08:12:31 GMT",
    }

    response = session.get(url, headers=headers_to_send)

    headers_sent = response.json()["headers"]

    assert response.status_code == 200

    for header, value in headers_to_send.items():
        assert headers_sent.get(header) == value
