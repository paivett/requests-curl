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


def test_build_headers_option_with_no_data():
    prepared_request = PreparedRequest()
    prepared_request.prepare(
        url="http://somefakeurl",
        headers={}
    )
    curl_request = CURLRequest(prepared_request)

    expected_headers = ["Content-Length: 0"]

    assert curl_request.build_headers_option() == (pycurl.HTTPHEADER, expected_headers)


def test_build_headers_option_with_some_data():
    prepared_request = PreparedRequest()
    prepared_request.prepare(
        url="http://somefakeurl",
        data="somedata",
        headers={}
    )
    curl_request = CURLRequest(prepared_request)

    expected_headers = ["Content-Length: 8"]

    assert curl_request.build_headers_option() == (pycurl.HTTPHEADER, expected_headers)


def test_build_headers_option_with_some_extra_headers():
    prepared_request = PreparedRequest()
    prepared_request.prepare(
        url="http://somefakeurl",
        data="someotherrandomdata",
        headers={
            "Content-Language": "en-US",
        }
    )
    curl_request = CURLRequest(prepared_request)

    expected_headers = [
        "Content-Length: 19",
        "Content-Language: en-US",
    ]

    opt_name, opt_value = curl_request.build_headers_option()

    assert (opt_name, sorted(opt_value)) == (pycurl.HTTPHEADER, sorted(expected_headers))


def test_build_get_options():
    prepared_request = PreparedRequest()
    prepared_request.prepare(
        url="http://somefakeurl",
        method="GET",
    )
    curl_request = CURLRequest(prepared_request)

    assert curl_request.build_http_method_options() == tuple()


def test_build_head_options():
    prepared_request = PreparedRequest()
    prepared_request.prepare(
        url="http://somefakeurl",
        method="HEAD",
    )
    curl_request = CURLRequest(prepared_request)

    expected_options = (
        (pycurl.CUSTOMREQUEST, "HEAD"),
    )

    assert curl_request.build_http_method_options() == expected_options


def test_build_delete_options():
    prepared_request = PreparedRequest()
    prepared_request.prepare(
        url="http://somefakeurl",
        method="DELETE",
    )
    curl_request = CURLRequest(prepared_request)

    expected_options = (
        (pycurl.CUSTOMREQUEST, "DELETE"),
    )

    assert curl_request.build_http_method_options() == expected_options


def test_build_post_options():
    prepared_request = PreparedRequest()
    prepared_request.prepare(
        url="http://somefakeurl",
        method="POST",
    )
    curl_request = CURLRequest(prepared_request)

    expected_options = (
        (pycurl.CUSTOMREQUEST, "POST"),
    )

    assert curl_request.build_http_method_options() == expected_options


def test_build_put_options():
    prepared_request = PreparedRequest()
    prepared_request.prepare(
        url="http://somefakeurl",
        method="PUT",
    )
    curl_request = CURLRequest(prepared_request)

    expected_options = (
        (pycurl.CUSTOMREQUEST, "PUT"),
    )

    assert curl_request.build_http_method_options() == expected_options


def test_build_patch_options():
    prepared_request = PreparedRequest()
    prepared_request.prepare(
        url="http://somefakeurl",
        method="PATCH",
    )
    curl_request = CURLRequest(prepared_request)

    expected_options = (
        (pycurl.CUSTOMREQUEST, "PATCH"),
    )

    assert curl_request.build_http_method_options() == expected_options


def test_build_options_options():
    prepared_request = PreparedRequest()
    prepared_request.prepare(
        url="http://somefakeurl",
        method="OPTIONS",
    )
    curl_request = CURLRequest(prepared_request)

    expected_options = (
        (pycurl.CUSTOMREQUEST, "OPTIONS"),
    )

    assert curl_request.build_http_method_options() == expected_options


def test_build_body_options_for_method_with_no_body():
    prepared_request = PreparedRequest()
    prepared_request.prepare(
        url="http://somefakeurl",
        method="GET",
    )
    curl_request = CURLRequest(prepared_request)

    expected_options = tuple()

    assert curl_request.build_body_options() == expected_options


def test_build_body_options_for_head_method():
    prepared_request = PreparedRequest()
    prepared_request.prepare(
        url="http://somefakeurl",
        method="HEAD",
        data="somedata",
    )
    curl_request = CURLRequest(prepared_request)

    expected_options = (
        (pycurl.NOBODY, True),
    )

    assert curl_request.build_body_options() == expected_options


@pytest.mark.parametrize("data, expected_data", (
    ("somedata", b"somedata"),
    ("some-ütf8-data", b"some-\xc3\xbctf8-data"),
))
def test_build_body_options_with_some_string_data(data, expected_data):
    prepared_request = PreparedRequest()
    prepared_request.prepare(
        url="http://somefakeurl",
        method="POST",
        data=data,
    )
    curl_request = CURLRequest(prepared_request)

    curl_options = curl_request.build_body_options()

    assert curl_options[0] == (pycurl.UPLOAD, True)

    assert curl_options[1][0] == pycurl.READFUNCTION
    # We actually call the function to test that it reads
    # the expected bytes
    assert curl_options[1][1]() == expected_data


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
def test_build_body_options_with_some_form_data(form, expected_encoded_form):
    prepared_request = PreparedRequest()
    prepared_request.prepare(
        url="http://somefakeurl",
        method="POST",
        data=form,
    )
    curl_request = CURLRequest(prepared_request)

    curl_options = curl_request.build_body_options()

    assert curl_options == ((pycurl.POSTFIELDS, expected_encoded_form),)


def test_build_body_options_with_some_file_data(tmpdir):
    p = tmpdir.join("test.txt")
    p.write("content")
    prepared_request = PreparedRequest()
    prepared_request.prepare(
        url="http://somefakeurl",
        method="POST",
        data=p,
    )
    curl_request = CURLRequest(prepared_request)

    curl_options = curl_request.build_body_options()

    assert curl_options[0] == (pycurl.UPLOAD, True)

    assert curl_options[1][0] == pycurl.READFUNCTION
    # We actually call the function to test that it reads
    # the expected bytes
    assert curl_options[1][1]() == "content"


def test_build_timeout_options_with_no_timeout():
    prepared_request = PreparedRequest()
    prepared_request.prepare(
        url="http://somefakeurl",
    )
    curl_request = CURLRequest(prepared_request)

    assert curl_request.build_timeout_options() == tuple()


def test_build_timeout_options_with_some_seconds_timeout():
    prepared_request = PreparedRequest()
    prepared_request.prepare(
        url="http://somefakeurl",
    )
    curl_request = CURLRequest(prepared_request, timeout=3.2)

    assert curl_request.build_timeout_options() == ((pycurl.TIMEOUT_MS, 3200),)


@pytest.mark.parametrize("timeout", (
    (1.234, 1),
    [1.234, 1],
))
def test_build_timeout_options_with_a_pair_of_seconds_timeout(timeout):
    prepared_request = PreparedRequest()
    prepared_request.prepare(
        url="http://somefakeurl",
    )
    curl_request = CURLRequest(prepared_request, timeout=timeout)

    expected_options = (
        (pycurl.TIMEOUT_MS, 2234),
        (pycurl.CONNECTTIMEOUT_MS, 1234),
    )

    assert curl_request.build_timeout_options() == expected_options


def test_build_ca_options_with_no_verify():
    prepared_request = PreparedRequest()
    prepared_request.prepare(
        url="http://somefakeurl",
    )
    curl_request = CURLRequest(prepared_request)

    expected_options = (
        (pycurl.SSL_VERIFYHOST, 0),
        (pycurl.SSL_VERIFYPEER, 0),
    )

    assert curl_request.build_ca_options() == expected_options


def test_build_ca_options_with_verify_as_true():
    prepared_request = PreparedRequest()
    prepared_request.prepare(
        url="http://somefakeurl",
    )
    curl_request = CURLRequest(prepared_request, verify=True)

    expected_options = (
        (pycurl.SSL_VERIFYHOST, 2),
        (pycurl.SSL_VERIFYPEER, 2),
        (pycurl.CAINFO, DEFAULT_CA_BUNDLE_PATH),
    )

    assert curl_request.build_ca_options() == expected_options


def test_build_ca_options_with_ca_file(tmpdir):
    pem_path = str(tmpdir.join("some.pem").ensure())
    prepared_request = PreparedRequest()
    prepared_request.prepare(
        url="http://somefakeurl",
    )
    curl_request = CURLRequest(prepared_request, verify=pem_path)

    expected_options = (
        (pycurl.SSL_VERIFYHOST, 2),
        (pycurl.SSL_VERIFYPEER, 2),
        (pycurl.CAINFO, pem_path),
    )

    assert curl_request.build_ca_options() == expected_options


def test_build_ca_options_with_ca_path(tmpdir):
    pem_path = str(tmpdir.mkdir("some_path"))
    prepared_request = PreparedRequest()
    prepared_request.prepare(
        url="http://somefakeurl",
    )
    curl_request = CURLRequest(prepared_request, verify=pem_path)

    expected_options = (
        (pycurl.SSL_VERIFYHOST, 2),
        (pycurl.SSL_VERIFYPEER, 2),
        (pycurl.CAPATH, pem_path),
    )

    assert curl_request.build_ca_options() == expected_options


def test_build_cert_options_with_no_cert():
    prepared_request = PreparedRequest()
    prepared_request.prepare(
        url="http://somefakeurl",
    )
    curl_request = CURLRequest(prepared_request)

    assert curl_request.build_cert_options() == tuple()


def test_build_cert_options_with_cert():
    prepared_request = PreparedRequest()
    prepared_request.prepare(
        url="http://somefakeurl",
    )
    curl_request = CURLRequest(prepared_request, cert="/some/path")

    assert curl_request.build_cert_options() == ((pycurl.SSLCERT, "/some/path"),)


def test_build_cert_options_with_cert_and_key():
    prepared_request = PreparedRequest()
    prepared_request.prepare(
        url="http://somefakeurl",
    )
    curl_request = CURLRequest(prepared_request, cert=("/some/path", "key"))

    expected_options = (
        (pycurl.SSLCERT, "/some/path"),
        (pycurl.SSLKEY, "key"),
    )

    assert curl_request.build_cert_options() == expected_options
