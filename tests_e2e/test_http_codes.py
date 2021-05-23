import pytest
import requests

from requests_curl.adapter import CURLAdapter


@pytest.mark.parametrize(
    "method",
    (
        "get",
        "post",
        "put",
        "delete",
        "patch",
    ),
)
@pytest.mark.parametrize(
    "http_code",
    (
        200,
        300,
        400,
        500,
    ),
)
def test_http_codes(method, http_code):
    session = requests.Session()
    session_with_curl = requests.Session()

    session_with_curl.mount("http://", CURLAdapter())

    url = f"http://http_bin/status/{http_code}"

    response = getattr(session, method)(url)
    response_with_curl = getattr(session_with_curl, method)(url)

    headers = response.headers
    headers_with_curl = response_with_curl.headers

    # Since date may vary, we remove it from assert
    headers.pop("Date")
    headers_with_curl.pop("Date")

    assert response_with_curl.status_code == http_code
    assert headers_with_curl == headers
    assert response_with_curl.url == response.url
    assert response_with_curl.text == response.text
