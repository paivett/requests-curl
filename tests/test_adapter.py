import pytest
import pycurl

from collections import deque

from requests import PreparedRequest
from requests.exceptions import (
    ConnectionError,
    ReadTimeout,
    SSLError,
    ProxyError,
    ConnectTimeout,
)

from requests_curl.adapter import CURLAdapter
from requests_curl.response import CURLResponse


def test_create_adapter_with_default_retries():
    adapter = CURLAdapter()

    assert adapter.max_retries.total == 0


def test_create_adapter_with_custom_retries():
    adapter = CURLAdapter(max_retries=42)

    assert adapter.max_retries.total == 42


class FakePool:
    def __init__(self):
        self._response_data = deque()

    def add_response(self, status, body, header_lines):
        self._response_data.append((status, body, header_lines))

    def add_exception(self, exception):
        self._response_data.append(exception)

    def send(self, curl_request):
        response_data = self._response_data.popleft()

        if isinstance(response_data, Exception):
            raise response_data
        else:
            response = CURLResponse(curl_request)
            response.status = response_data[0]
            response.body.write(response_data[1])
            response.add_headers_from_raw_lines(response_data[2])

            return response


class FakePoolProvider:
    def __init__(self, *args, **kwargs):
        self._pools = {}
        self._cleared = False

    def add_pool_for_url(self, url, pool):
        self._pools[url] = pool

    def add_pool_for_proxied_url(self, proxy_url, url, pool):
        self._pools[(proxy_url, url)] = pool

    def get_pool_for_url(self, url):
        return self._pools[url]

    def get_pool_for_proxied_url(self, proxy_url, url):
        return self._pools[(proxy_url, url)]

    def clear(self):
        self._cleared = True

    @property
    def cleared(self):
        return self._cleared


def test_adapter_performs_a_successful_request():
    request = PreparedRequest()
    request.prepare(url="http://somefakeurl", method="GET", headers={})

    header_lines = [
        b"HTTP/1.1 200 OK\n",
        b"Content-Language: en-US\n",
    ]
    pool = FakePool()
    pool.add_response(200, b"somebodydata", header_lines)
    pool_provider = FakePoolProvider()
    pool_provider.add_pool_for_url(request.url, pool)

    adapter = CURLAdapter(pool_provider_factory=lambda *args, **kwargs: pool_provider)

    response = adapter.send(request)

    assert response.status_code == 200
    assert response.text == "somebodydata"
    assert response.headers == {"Content-Language": "en-US"}


def test_adapter_performs_retry_after_an_exception():
    request = PreparedRequest()
    request.prepare(url="http://somefakeurl", method="GET", headers={})

    header_lines = [
        b"HTTP/1.1 200 OK\n",
        b"Content-Language: en-US\n",
    ]
    pool = FakePool()
    pool.add_exception(ConnectionError())
    pool.add_response(200, b"somebodydata", header_lines)
    pool_provider = FakePoolProvider()
    pool_provider.add_pool_for_url(request.url, pool)

    adapter = CURLAdapter(
        max_retries=1, pool_provider_factory=lambda *args, **kwargs: pool_provider
    )

    response = adapter.send(request)

    assert response.status_code == 200
    assert response.text == "somebodydata"
    assert response.headers == {"Content-Language": "en-US"}


def test_adapter_reaches_max_retries_and_raises_exception():
    request = PreparedRequest()
    request.prepare(url="http://somefakeurl", method="GET", headers={})

    pool = FakePool()
    pool.add_exception(ConnectionError())
    pool.add_exception(ReadTimeout())
    pool_provider = FakePoolProvider()
    pool_provider.add_pool_for_url(request.url, pool)

    adapter = CURLAdapter(
        max_retries=1, pool_provider_factory=lambda *args, **kwargs: pool_provider
    )

    with pytest.raises(ReadTimeout):
        adapter.send(request)


@pytest.mark.parametrize(
    "error_code, error_msg, expected_exception",
    (
        (pycurl.E_SSL_CACERT, "some ssl error", SSLError),
        (pycurl.E_SSL_CACERT_BADFILE, "some ssl error", SSLError),
        (pycurl.E_SSL_CERTPROBLEM, "some ssl error", SSLError),
        (pycurl.E_SSL_CIPHER, "some ssl error", SSLError),
        (pycurl.E_SSL_CONNECT_ERROR, "some ssl error", SSLError),
        (pycurl.E_SSL_CRL_BADFILE, "some ssl error", SSLError),
        (pycurl.E_SSL_ENGINE_INITFAILED, "some ssl error", SSLError),
        (pycurl.E_SSL_ENGINE_NOTFOUND, "some ssl error", SSLError),
        (pycurl.E_SSL_ENGINE_SETFAILED, "some ssl error", SSLError),
        (pycurl.E_SSL_INVALIDCERTSTATUS, "some ssl error", SSLError),
        (pycurl.E_SSL_ISSUER_ERROR, "some ssl error", SSLError),
        (pycurl.E_SSL_PEER_CERTIFICATE, "some ssl error", SSLError),
        (pycurl.E_SSL_PINNEDPUBKEYNOTMATCH, "some ssl error", SSLError),
        (pycurl.E_SSL_SHUTDOWN_FAILED, "some ssl error", SSLError),
        (pycurl.E_OPERATION_TIMEOUTED, "Connection timed out", ConnectTimeout),
        (pycurl.E_OPERATION_TIMEDOUT, "Connection timed out", ConnectTimeout),
        (pycurl.E_OPERATION_TIMEOUTED, "Some other time error", ReadTimeout),
        (pycurl.E_OPERATION_TIMEDOUT, "Some other time error", ReadTimeout),
        (pycurl.E_COULDNT_RESOLVE_PROXY, "Resolve proxy error", ProxyError),
        (
            pycurl.E_RECV_ERROR,
            "Received HTTP code 407 from proxy after CONNECT",
            ProxyError,
        ),
        (pycurl.E_GOT_NOTHING, "Some misterious error", ConnectionError),
    ),
)
def test_adapter_translates_from_pycurl_errors(
    error_code, error_msg, expected_exception
):
    request = PreparedRequest()
    request.prepare(url="http://somefakeurl", method="GET", headers={})

    pool = FakePool()
    pool.add_exception(pycurl.error(error_code, error_msg))
    pool_provider = FakePoolProvider()
    pool_provider.add_pool_for_url(request.url, pool)

    adapter = CURLAdapter(pool_provider_factory=lambda *args, **kwargs: pool_provider)

    with pytest.raises(expected_exception):
        adapter.send(request)


def test_adapter_clears_pool_provider_after_close():
    pool_provider = FakePoolProvider()

    adapter = CURLAdapter(
        max_retries=1, pool_provider_factory=lambda *args, **kwargs: pool_provider
    )

    adapter.close()

    assert pool_provider.cleared


def test_adapter_performs_a_successful_request_through_proxy():
    request = PreparedRequest()
    request.prepare(url="http://somefakeurl", method="GET", headers={})

    proxies = {
        "http": "http://localhost:8080",
        "https": "https://localhost:8081",
    }

    header_lines = [
        b"HTTP/1.1 200 OK\n",
        b"Content-Language: en-US\n",
    ]
    pool = FakePool()
    pool.add_response(200, b"data obtained through proxy", header_lines)
    pool_provider = FakePoolProvider()
    pool_provider.add_pool_for_proxied_url("http://localhost:8080", request.url, pool)

    adapter = CURLAdapter(pool_provider_factory=lambda *args, **kwargs: pool_provider)

    response = adapter.send(request, proxies=proxies)

    assert response.status_code == 200
    assert response.text == "data obtained through proxy"
    assert response.headers == {"Content-Language": "en-US"}
