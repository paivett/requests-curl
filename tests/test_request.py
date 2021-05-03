# -*- coding: utf-8 -*
import pycurl
import pytest
import six

from requests import PreparedRequest
from requests.adapters import DEFAULT_CA_BUNDLE_PATH
from requests_curl.request import CURLRequest


def test_request_property():
    prepared_request = PreparedRequest()
    curl_request = CURLRequest(prepared_request)

    assert curl_request.request is prepared_request


def test_use_chunked_upload_is_false_for_json():
    prepared_request = PreparedRequest()
    json_data = {"somekey": "somedata"}
    prepared_request.prepare(
        url="http://somefakeurl",
        json=json_data,
    )
    curl_request = CURLRequest(prepared_request)

    assert curl_request.use_chunked_upload is False


def test_use_chunked_upload_is_false_for_string_data():
    prepared_request = PreparedRequest()
    some_data = "this is some data as string"
    prepared_request.prepare(
        url="http://somefakeurl",
        data=some_data,
    )
    curl_request = CURLRequest(prepared_request)

    assert curl_request.use_chunked_upload is False


def test_use_chunked_upload_is_true_for_streamed_data():
    prepared_request = PreparedRequest()
    some_stream_data = six.StringIO("this is some data as string")
    prepared_request.prepare(
        url="http://somefakeurl",
        data=some_stream_data,
    )
    curl_request = CURLRequest(prepared_request)

    assert curl_request.use_chunked_upload is True


def test_curl_option_with_no_data_nor_headers():
    prepared_request = PreparedRequest()
    prepared_request.prepare(
        url="http://somefakeurl",
        headers={},
        method="GET",
    )
    curl_request = CURLRequest(prepared_request)

    expected_options = {
        pycurl.URL: "http://somefakeurl/",
        pycurl.HTTPHEADER: [],
        pycurl.SSL_VERIFYHOST: 0,
        pycurl.SSL_VERIFYPEER: 0,
    }
    
    curl_options = curl_request.options

    assert sorted(curl_options.items()) == sorted(expected_options.items())


def test_curl_options_with_some_extra_headers():
    prepared_request = PreparedRequest()
    prepared_request.prepare(
        url="http://somefakeurl",
        method="GET",
        headers={
            "Content-Language": "en-US",
            "Cache-Control": "no-cache",
        }
    )
    curl_request = CURLRequest(prepared_request)

    curl_options = curl_request.options

    expected_headers = sorted([
        "Cache-Control: no-cache",
        "Content-Language: en-US",
    ])

    assert len(curl_options) == 4
    assert curl_options[pycurl.URL] == "http://somefakeurl/"
    assert curl_options[pycurl.SSL_VERIFYHOST] == 0
    assert curl_options[pycurl.SSL_VERIFYPEER] == 0
    assert sorted(curl_options[pycurl.HTTPHEADER]) == expected_headers


def test_curl_options_for_head():
    prepared_request = PreparedRequest()
    prepared_request.prepare(
        url="http://somefakeurl",
        method="HEAD",
        headers={
            "Cache-Control": "no-cache",
        }
    )
    curl_request = CURLRequest(prepared_request)

    expected_options = {
        pycurl.URL: "http://somefakeurl/",
        pycurl.HTTPHEADER: ["Cache-Control: no-cache"],
        pycurl.SSL_VERIFYHOST: 0,
        pycurl.SSL_VERIFYPEER: 0,
        pycurl.CUSTOMREQUEST: "HEAD",
        pycurl.NOBODY: True,
    }
    
    curl_options = curl_request.options

    assert sorted(curl_options.items()) == sorted(expected_options.items())


def test_curl_options_for_delete():
    prepared_request = PreparedRequest()
    prepared_request.prepare(
        url="http://somefakeurl",
        method="DELETE",
    )
    curl_request = CURLRequest(prepared_request)

    expected_options = {
        pycurl.URL: "http://somefakeurl/",
        pycurl.HTTPHEADER: ["Content-Length: 0"],
        pycurl.SSL_VERIFYHOST: 0,
        pycurl.SSL_VERIFYPEER: 0,
        pycurl.CUSTOMREQUEST: "DELETE",
    }
    
    curl_options = curl_request.options

    assert sorted(curl_options.items()) == sorted(expected_options.items())


@pytest.mark.parametrize("data, expected_data", (
    ("somedata", b"somedata"),
    ("some-ütf8-data", b"some-\xc3\xbctf8-data"),
))
@pytest.mark.parametrize("http_method", ("POST", "PUT"))
def test_curl_options_for_post_put_with_some_string_data(http_method, data, expected_data):
    prepared_request = PreparedRequest()
    prepared_request.prepare(
        url="http://somefakeurl",
        method=http_method,
        data=data,
    )
    curl_request = CURLRequest(prepared_request)

    curl_options = curl_request.options

    expected_headers = [
        f"Content-Length: {len(data)}",
    ]

    assert len(curl_options) == 7
    assert curl_options[pycurl.URL] == "http://somefakeurl/"
    assert curl_options[pycurl.SSL_VERIFYHOST] == 0
    assert curl_options[pycurl.SSL_VERIFYPEER] == 0
    assert curl_options[pycurl.UPLOAD] is True
    assert curl_options[pycurl.CUSTOMREQUEST] == http_method
    assert curl_options[pycurl.HTTPHEADER] == expected_headers

    # We actually call the function to test that it reads
    # the expected bytes
    assert curl_options[pycurl.READFUNCTION]() == expected_data


@pytest.mark.parametrize("form, expected_encoded_form", (
    (
        {"field1": "data1", "field2": "data2"},
        "field1=data1&field2=data2",
    ),
    (
        [("field1", "data1"), ("field2", "data2")],
        "field1=data1&field2=data2",
    ),
    (
        {"field1": "data1", "field2": "datüm"},
        "field1=data1&field2=dat%C3%BCm",
    ),
))
def test_curl_option_for_post_with_body_with_form_data(form, expected_encoded_form):
    prepared_request = PreparedRequest()
    prepared_request.prepare(
        url="http://somefakeurl",
        method="POST",
        data=form,
    )
    curl_request = CURLRequest(prepared_request)

    curl_options = curl_request.options

    expected_headers = sorted([
        f"Content-Length: {len(expected_encoded_form)}",
        "Content-Type: application/x-www-form-urlencoded",
    ])

    assert len(curl_options) == 6
    assert curl_options[pycurl.URL] == "http://somefakeurl/"
    assert curl_options[pycurl.SSL_VERIFYHOST] == 0
    assert curl_options[pycurl.SSL_VERIFYPEER] == 0
    assert curl_options[pycurl.CUSTOMREQUEST] == "POST"
    assert sorted(curl_options[pycurl.HTTPHEADER]) == expected_headers
    assert curl_options[pycurl.POSTFIELDS] == expected_encoded_form


def test_curl_options_for_post_with_some_file_data(tmpdir):
    p = tmpdir.join("test.txt")
    p.write("content")
    prepared_request = PreparedRequest()
    prepared_request.prepare(
        url="http://somefakeurl",
        method="POST",
        data=p,
    )
    curl_request = CURLRequest(prepared_request)

    curl_options = curl_request.options

    expected_headers = []

    assert len(curl_options) == 7
    assert curl_options[pycurl.URL] == "http://somefakeurl/"
    assert curl_options[pycurl.SSL_VERIFYHOST] == 0
    assert curl_options[pycurl.SSL_VERIFYPEER] == 0
    assert curl_options[pycurl.UPLOAD] is True
    assert curl_options[pycurl.CUSTOMREQUEST] == "POST"
    assert curl_options[pycurl.HTTPHEADER] == expected_headers

    # We actually call the function to test that it reads
    # the expected bytes
    assert curl_options[pycurl.READFUNCTION]() == "content"


def test_curl_options_for_patch():
    prepared_request = PreparedRequest()
    prepared_request.prepare(
        url="http://somefakeurl",
        method="PATCH",
    )
    curl_request = CURLRequest(prepared_request)

    expected_options = {
        pycurl.URL: "http://somefakeurl/",
        pycurl.HTTPHEADER: ["Content-Length: 0"],
        pycurl.SSL_VERIFYHOST: 0,
        pycurl.SSL_VERIFYPEER: 0,
        pycurl.CUSTOMREQUEST: "PATCH",
    }
    
    curl_options = curl_request.options

    assert sorted(curl_options.items()) == sorted(expected_options.items())


def test_curl_options_for_options():
    prepared_request = PreparedRequest()
    prepared_request.prepare(
        url="http://somefakeurl",
        method="OPTIONS",
    )
    curl_request = CURLRequest(prepared_request)

    expected_options = {
        pycurl.URL: "http://somefakeurl/",
        pycurl.HTTPHEADER: ["Content-Length: 0"],
        pycurl.SSL_VERIFYHOST: 0,
        pycurl.SSL_VERIFYPEER: 0,
        pycurl.CUSTOMREQUEST: "OPTIONS",
    }
    
    curl_options = curl_request.options

    assert sorted(curl_options.items()) == sorted(expected_options.items())


def test_curl_options_for_get_with_timeout_in_seconds():
    prepared_request = PreparedRequest()
    prepared_request.prepare(
        url="http://somefakeurl",
        method="GET",
    )
    curl_request = CURLRequest(prepared_request, timeout=3.2)

    expected_options = {
        pycurl.URL: "http://somefakeurl/",
        pycurl.HTTPHEADER: [],
        pycurl.SSL_VERIFYHOST: 0,
        pycurl.SSL_VERIFYPEER: 0,
        pycurl.TIMEOUT_MS: 3200,
    }

    curl_options = curl_request.options

    assert sorted(curl_options.items()) == sorted(expected_options.items())


@pytest.mark.parametrize("timeout", (
    (1.234, 1),
    [1.234, 1],
))
def test_curl_options_for_get_with_multi_timeout_values(timeout):
    prepared_request = PreparedRequest()
    prepared_request.prepare(
        url="http://somefakeurl",
        method="GET",
    )
    curl_request = CURLRequest(prepared_request, timeout=timeout)
  
    expected_options = {
        pycurl.URL: "http://somefakeurl/",
        pycurl.HTTPHEADER: [],
        pycurl.SSL_VERIFYHOST: 0,
        pycurl.SSL_VERIFYPEER: 0,
        pycurl.TIMEOUT_MS: 2234,
        pycurl.CONNECTTIMEOUT_MS: 1234,
    }

    curl_options = curl_request.options

    assert sorted(curl_options.items()) == sorted(expected_options.items())


def test_curl_options_for_get_with_verify_as_true():
    prepared_request = PreparedRequest()
    prepared_request.prepare(
        url="http://somefakeurl",
        method="GET",
    )
    curl_request = CURLRequest(prepared_request, verify=True)

    expected_options = {
        pycurl.URL: "http://somefakeurl/",
        pycurl.HTTPHEADER: [],
        pycurl.SSL_VERIFYHOST: 2,
        pycurl.SSL_VERIFYPEER: 2,
        pycurl.CAINFO: DEFAULT_CA_BUNDLE_PATH,
    }

    curl_options = curl_request.options

    assert sorted(curl_options.items()) == sorted(expected_options.items())


def test_curl_options_for_get_with_ca_file(tmpdir):
    pem_path = str(tmpdir.join("some.pem").ensure())
    prepared_request = PreparedRequest()
    prepared_request.prepare(
        url="http://somefakeurl",
        method="GET",
    )
    curl_request = CURLRequest(prepared_request, verify=pem_path)

    expected_options = {
        pycurl.URL: "http://somefakeurl/",
        pycurl.HTTPHEADER: [],
        pycurl.SSL_VERIFYHOST: 2,
        pycurl.SSL_VERIFYPEER: 2,
        pycurl.CAINFO: pem_path,
    }

    curl_options = curl_request.options

    assert sorted(curl_options.items()) == sorted(expected_options.items())


def test_burl_options_for_get_with_ca_path(tmpdir):
    pem_path = str(tmpdir.mkdir("some_path"))
    prepared_request = PreparedRequest()
    prepared_request.prepare(
        url="http://somefakeurl",
        method="GET",
    )
    curl_request = CURLRequest(prepared_request, verify=pem_path)

    expected_options = {
        pycurl.URL: "http://somefakeurl/",
        pycurl.HTTPHEADER: [],
        pycurl.SSL_VERIFYHOST: 2,
        pycurl.SSL_VERIFYPEER: 2,
        pycurl.CAPATH: pem_path,
    }

    curl_options = curl_request.options

    assert sorted(curl_options.items()) == sorted(expected_options.items())


def test_curl_options_for_get_with_cert():
    prepared_request = PreparedRequest()
    prepared_request.prepare(
        url="http://somefakeurl",
        method="GET",
    )
    curl_request = CURLRequest(prepared_request, verify=True, cert="/some/path")

    expected_options = {
        pycurl.URL: "http://somefakeurl/",
        pycurl.HTTPHEADER: [],
        pycurl.SSL_VERIFYHOST: 2,
        pycurl.SSL_VERIFYPEER: 2,
        pycurl.CAINFO: DEFAULT_CA_BUNDLE_PATH,
        pycurl.SSLCERT: "/some/path",
    }

    curl_options = curl_request.options

    assert sorted(curl_options.items()) == sorted(expected_options.items())


def test_curl_options_for_get_with_cert_and_key():
    prepared_request = PreparedRequest()
    prepared_request.prepare(
        url="http://somefakeurl",
        method="GET",
    )
    curl_request = CURLRequest(prepared_request, verify=True, cert=("/some/path", "key"))

    expected_options = {
        pycurl.URL: "http://somefakeurl/",
        pycurl.HTTPHEADER: [],
        pycurl.SSL_VERIFYHOST: 2,
        pycurl.SSL_VERIFYPEER: 2,
        pycurl.CAINFO: DEFAULT_CA_BUNDLE_PATH,
        pycurl.SSLCERT: "/some/path",
        pycurl.SSLKEY: "key",
    }

    curl_options = curl_request.options

    assert sorted(curl_options.items()) == sorted(expected_options.items())
