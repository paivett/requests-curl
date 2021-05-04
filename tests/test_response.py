import pytest

from requests import PreparedRequest, Response
from requests_curl.response import CURLResponse
from requests_curl.request import CURLRequest


def test_create_empty_curl_response():
    prepared_request = PreparedRequest()
    prepared_request.prepare(
        url="http://somefakeurl",
        method="GET",
        headers={}
    )
    curl_request = CURLRequest(prepared_request)

    response = CURLResponse(curl_request)

    assert response.curl_request is curl_request
    assert response.request is curl_request.request
    assert response.http_code is None
    assert not response.headers
    assert response.reason is None


def test_empty_curl_response_to_request_response():
    prepared_request = PreparedRequest()
    prepared_request.prepare(
        url="http://somefakeurl",
        method="GET",
        headers={}
    )
    curl_request = CURLRequest(prepared_request)

    response = CURLResponse(curl_request)
    response.http_code = 200

    req_response = response.to_requests_response()

    assert isinstance(req_response, Response)
    assert req_response.status_code == 200
    assert not req_response.headers
    assert not req_response.text
    assert req_response.url == "http://somefakeurl/"


def test_curl_response_with_data_and_headers_to_request_response():
    prepared_request = PreparedRequest()
    prepared_request.prepare(
        url="http://somefakeurl",
        method="GET",
        headers={}
    )
    curl_request = CURLRequest(prepared_request)

    expected_headers = {
        "Content-Language": "en-US",
        "Cache-Control": "no-cache",
    }

    response = CURLResponse(curl_request)
    response.http_code = 200
    response.headers = expected_headers
    response.body.write(b"someresponsedata") 

    req_response = response.to_requests_response()

    assert sorted(req_response.headers.items()) == sorted(expected_headers.items())


@pytest.mark.parametrize("header_lines, expected_headers", (
    (
        ["Content-Language: en-US",],
        {"Content-Language": "en-US",},
    ),
    (
        ["Content-Language: en-US", "Cache-Control: no-cache",],
        {"Content-Language": "en-US", "Cache-Control": "no-cache",},
    ),
    (
        ["Content-Language: en-US", "not-a-header", "Cache-Control: no-cache",],
        {"Content-Language": "en-US", "Cache-Control": "no-cache",},
    ),
))
def test_curl_response_parse_header_line(header_lines, expected_headers):
    prepared_request = PreparedRequest()
    prepared_request.prepare(
        url="http://somefakeurl",
        method="GET",
        headers={}
    )
    curl_request = CURLRequest(prepared_request)

    response = CURLResponse(curl_request)
    
    for header_line in header_lines:
        # We provide lines encoded as defined in http standard
        response.parse_header_line(header_line.encode("iso-8859-1"))
    
    assert sorted(response.headers.items()) == sorted(expected_headers.items())
