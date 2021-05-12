import pycurl
import pytest

from requests import PreparedRequest
from urllib3.util import parse_url

from requests_curl.pool import CURLHandlerPool, ClosedPool, EmptyPool, ProxyCURLHandlerPool
from requests_curl.request import CURLRequest


class FakeCurlHandler:
    
    def __init__(self) :
        self.options = {}
        self._performed = False
        self._open = True
        self.http_status = None
        self.header_lines = []
        self.body = b""

    def setopt(self, opt, value):
        self.options[opt] = value

    def getinfo(self, opt):
        return self.http_status

    def _write_body(self):
        write_func = self.options[pycurl.WRITEFUNCTION]
        write_func(self.body)
    
    def _write_headers(self):
        add_header_func = self.options[pycurl.HEADERFUNCTION]
        for line in self.header_lines:
            add_header_func(line)

    def perform(self):
        if self.open:
            self._write_body()
            self._write_headers()
            self._performed = True
        else:
            raise RuntimeError("Cannot perform on a closed handler")

    def reset(self):
        self._performed = False

    @property
    def open(self):
        return self._open
    
    @property
    def performed(self):
        return self._performed

    def close(self):
        self._open = False


def test_pool_send_configures_handler_correctly():
    prepared_request = PreparedRequest()
    prepared_request.prepare(
        url="http://somefakeurl",
        method="GET",
        headers={}
    )
    curl_request = CURLRequest(prepared_request)
    curl_handler = FakeCurlHandler()

    # Configure the handler to return some body and headers
    curl_handler.body = b"somebodydata"
    curl_handler.http_status = 200
    curl_handler.header_lines = [
        "HTTP/1.1 200 OK\n".encode("iso-8859-1"),
        "Content-Language: en-US\n".encode("iso-8859-1"),
        "Cache-Control: no-cache\n".encode("iso-8859-1"),
    ]

    pool = CURLHandlerPool(curl_factory=lambda: curl_handler)

    response = pool.send(curl_request)

    assert curl_handler.performed

    assert response.body.getvalue() == b"somebodydata"
    assert response.http_code == 200
    assert response.headers == {
        "Cache-Control": "no-cache",
        "Content-Language": "en-US",
    }

    # Assert that the curl options from the requests were set to the handler
    for opt, val in curl_request.options.items():
        assert curl_handler.options[opt] == val


def test_pool_puts_back_handler_after_successful_send():
    prepared_request = PreparedRequest()
    prepared_request.prepare(
        url="http://somefakeurl",
        method="GET",
        headers={}
    )
    curl_request = CURLRequest(prepared_request)
    curl_handler = FakeCurlHandler()

    pool = CURLHandlerPool(curl_factory=lambda: curl_handler)

    pool.send(curl_request)

    # Since we have put back the handle, now we can ask for it and it should
    # be the same and only handle of this pool
    assert curl_handler is pool.get_handler_from_pool()


def test_pool_closes_all_handles_when_it_is_closed():
    curl_handler_1 = FakeCurlHandler()
    curl_handler_2 = FakeCurlHandler()

    handlers = [curl_handler_1, curl_handler_2]

    pool = CURLHandlerPool(maxsize=2, curl_factory=lambda: handlers.pop())

    assert curl_handler_1.open
    assert curl_handler_2.open
    
    pool.close()

    assert not curl_handler_1.open
    assert not curl_handler_2.open


def test_pool_close_is_idempotent(mocker):
    curl_handler_1 = FakeCurlHandler()
    curl_handler_2 = FakeCurlHandler()

    handlers = [curl_handler_1, curl_handler_2]

    pool = CURLHandlerPool(maxsize=2, curl_factory=lambda: handlers.pop())

    assert curl_handler_1.open
    assert curl_handler_2.open
    
    pool.close()
    pool.close()

    assert not curl_handler_1.open
    assert not curl_handler_2.open


def test_pool_does_not_provide_more_handlers_once_closed(mocker):
    curl_handler = FakeCurlHandler()

    pool = CURLHandlerPool(curl_factory=lambda: curl_handler)

    pool.close()

    with pytest.raises(ClosedPool):
        pool.get_handler_from_pool()


def test_pool_fails_after_returning_all_handlers(mocker):
    curl_handler_1 = FakeCurlHandler()
    curl_handler_2 = FakeCurlHandler()

    handlers = [curl_handler_1, curl_handler_2]

    pool = CURLHandlerPool(maxsize=2, curl_factory=lambda: handlers.pop())

    pool.get_handler_from_pool()
    pool.get_handler_from_pool()

    with pytest.raises(EmptyPool):
        pool.get_handler_from_pool()


def test_returning_a_handler_after_pool_closed_does_not_fail(mocker):
    pool = CURLHandlerPool(curl_factory=lambda: FakeCurlHandler())

    handler = pool.get_handler_from_pool()

    pool.close()

    # No exception is thrown
    pool.put_handler_back(handler)


def test_proxy_pool_configures_handler_with_proxy_optionsl(mocker):
    prepared_request = PreparedRequest()
    prepared_request.prepare(
        url="http://somefakeurl",
        method="GET",
        headers={}
    )
    curl_request = CURLRequest(prepared_request)
    curl_handler = FakeCurlHandler()

    # Configure the handler to return some body and headers
    curl_handler.body = b"somebodydata"
    curl_handler.http_status = 200
    curl_handler.header_lines = [
        "HTTP/1.1 200 OK\n".encode("iso-8859-1"),
        "Content-Language: en-US\n".encode("iso-8859-1"),
        "Cache-Control: no-cache\n".encode("iso-8859-1"),
    ]

    proxy_url = parse_url("http://localhost:8080")

    pool = ProxyCURLHandlerPool(proxy_url, curl_factory=lambda: curl_handler)

    response = pool.send(curl_request)

    assert curl_handler.performed

    assert response.body.getvalue() == b"somebodydata"
    assert response.http_code == 200
    assert response.headers == {
        "Cache-Control": "no-cache",
        "Content-Language": "en-US",
    }

    # Assert that the curl options from the requests were set to the handler
    for opt, val in curl_request.options.items():
        assert curl_handler.options[opt] == val

    # Finally, assert that the special proxy options were set
    assert curl_handler.options[pycurl.PROXY] == "localhost"
    assert curl_handler.options[pycurl.PROXYAUTH] == pycurl.HTTPAUTH_ANY
    assert curl_handler.options[pycurl.PROXYUSERPWD] == None
    assert curl_handler.options[pycurl.PROXYPORT] == 8080


def test_proxy_pool_configures_handler_with_proxy_user_and_password(mocker):
    prepared_request = PreparedRequest()
    prepared_request.prepare(
        url="http://somefakeurl",
        method="GET",
        headers={}
    )
    curl_request = CURLRequest(prepared_request)
    curl_handler = FakeCurlHandler()

    # Configure the handler to return some body and headers
    curl_handler.body = b"somebodydata"
    curl_handler.http_status = 200
    curl_handler.header_lines = [
        "HTTP/1.1 200 OK\n".encode("iso-8859-1"),
        "Content-Language: en-US\n".encode("iso-8859-1"),
        "Cache-Control: no-cache\n".encode("iso-8859-1"),
    ]

    proxy_url = parse_url("http://user:pwd@localhost:8080")

    pool = ProxyCURLHandlerPool(proxy_url, curl_factory=lambda: curl_handler)

    response = pool.send(curl_request)

    assert curl_handler.performed

    assert response.body.getvalue() == b"somebodydata"
    assert response.http_code == 200
    assert response.headers == {
        "Cache-Control": "no-cache",
        "Content-Language": "en-US",
    }

    # Assert that the curl options from the requests were set to the handler
    for opt, val in curl_request.options.items():
        assert curl_handler.options[opt] == val

    # Finally, assert that the special proxy options were set
    assert curl_handler.options[pycurl.PROXY] == "localhost"
    assert curl_handler.options[pycurl.PROXYAUTH] == pycurl.HTTPAUTH_ANY
    assert curl_handler.options[pycurl.PROXYUSERPWD] == "user:pwd"
    assert curl_handler.options[pycurl.PROXYPORT] == 8080