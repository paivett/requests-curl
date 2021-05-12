import pycurl

from requests import PreparedRequest

from requests_curl.pool import CURLHandlerPool
from requests_curl.request import CURLRequest


class FakeCurlHandler:
    
    def __init__(self) :
        self.options = {}
        self.performed = False
        self.open = True
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
            self.performed = True
        else:
            raise RuntimeError("Cannot perform on a closed handler")

    def reset(self):
        self.performed = False
    
    def close(self):
        self.open = False


def test_pool_send_configures_handler_correctly(mocker):
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
        assert curl_request.options[opt] == val
