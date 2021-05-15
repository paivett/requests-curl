import pytest
import requests

from requests_curl.adapter import CURLAdapter


@pytest.mark.parametrize("method", (
    "get", "post", "put", "delete", "patch",
))
def test_method(method):
    session = requests.Session()
    session_with_curl = requests.Session()

    session_with_curl.mount("http://", CURLAdapter())

    url = f"http://http_bin/{method}"

    response = getattr(session, method)(url)
    response_with_curl = getattr(session_with_curl, method)(url)

    headers = response.headers
    headers_with_curl = response_with_curl.headers

    # Since date may vary, we remove it from assert
    headers.pop("Date")
    headers_with_curl.pop("Date")

    assert response.status_code == 200
    assert response_with_curl.status_code == response.status_code
    assert headers_with_curl == headers
    assert response_with_curl.url == response.url
    assert response_with_curl.text == response.text