import pytest
import pycurl

from requests.exceptions import (
    ConnectionError, ConnectTimeout, ReadTimeout, SSLError,
    ProxyError, InvalidProxyURL,
    InvalidURL, RequestException
)

from requests_curl.error import translate_curl_exception


@pytest.mark.parametrize("error_code, error_msg, expected_exception", (
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
    (pycurl.E_RECV_ERROR, "Received HTTP code 407 from proxy after CONNECT", ProxyError),
    (pycurl.E_GOT_NOTHING, "Some misterious error", ConnectionError),
))
def test_translate_curl_exception(error_code, error_msg, expected_exception):
    curl_exception = pycurl.error(error_code, error_msg)
    translated_exception = translate_curl_exception(curl_exception)
    assert translated_exception == expected_exception
