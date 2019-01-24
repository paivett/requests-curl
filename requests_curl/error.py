import pycurl

from requests.exceptions import (
    ConnectionError, ConnectTimeout, ReadTimeout, SSLError,
    ProxyError, RetryError, InvalidSchema, InvalidProxyURL,
    InvalidURL, RequestException
)

PYCURL_SSL_ERRORS = (
    pycurl.E_SSL_CACERT,
    pycurl.E_SSL_CACERT_BADFILE,
    pycurl.E_SSL_CERTPROBLEM,
    pycurl.E_SSL_CIPHER,
    pycurl.E_SSL_CONNECT_ERROR,
    pycurl.E_SSL_CRL_BADFILE,
    pycurl.E_SSL_ENGINE_INITFAILED,
    pycurl.E_SSL_ENGINE_NOTFOUND,
    pycurl.E_SSL_ENGINE_SETFAILED,
    pycurl.E_SSL_INVALIDCERTSTATUS,
    pycurl.E_SSL_ISSUER_ERROR,
    pycurl.E_SSL_PEER_CERTIFICATE,
    pycurl.E_SSL_PINNEDPUBKEYNOTMATCH,
    pycurl.E_SSL_SHUTDOWN_FAILED
)


def translate_curl_exception(curl_exception):
    """This function will make the best effort to translate a given PyCURL error
    to a requests exception.

    Args:
        curl_exception (pycurl.error): PyCURL error to be translated.

    Returns:
        requests.exceptions.RequestException: the requests exception that
            matches to the CURL error.
    """

    error_code, error_msg = curl_exception.args

    if error_code in PYCURL_SSL_ERRORS:
        error_class = SSLError
    else:
        # This is kind of the default error
        error_class = ConnectionError

    return error_class
