"""Requests adapter implementing a CURL backend"""

import pycurl

from requests.exceptions import RequestException
from requests.adapters import (
    BaseAdapter, DEFAULT_CA_BUNDLE_PATH, DEFAULT_RETRIES,
    DEFAULT_POOLSIZE, DEFAULT_POOLBLOCK
)
from requests import Response as RequestResponse
from urllib3.util.retry import Retry
from urllib3.exceptions import MaxRetryError

from .pool import CURLHandlerPoolManager
from .error import translate_curl_exception
from .request import CURLRequest


class CURLAdapter(BaseAdapter):
    """A requests adapter implemented using PyCURL"""

    def __init__(self, max_retries=DEFAULT_RETRIES, initial_pool_size=DEFAULT_POOLSIZE,
                 max_pool_size=DEFAULT_POOLSIZE, pool_block=DEFAULT_POOLBLOCK):
        super(CURLAdapter, self).__init__()

        if max_retries == DEFAULT_RETRIES:
            self.max_retries = Retry(0, read=False)
        else:
            self.max_retries = Retry.from_int(max_retries)

        self._pool_manager = CURLHandlerPoolManager(max_pool_size=max_pool_size,
                                                    initial_pool_size=initial_pool_size,
                                                    pool_block=pool_block)

    def send(self, request, stream=False, timeout=None, verify=True, cert=None,
             proxies=None):
        """Sends PreparedRequest object using PyCURL. Returns Response object.

        Args:
            request (PreparedRequest): the request being sent.
            stream (bool, optional): Defaults to False. Whether to stream the
                request content.
            timeout (float, optional): Defaults to None. How long to wait for
                the server to send data before giving up, as a float, or a
                `(connect timeout, read timeout)` tuple.
            verify (bool, optional): Defaults to True. Either a boolean, in
                which case it controls whether we verify the server's TLS
                certificate, or a string, in which case it must be a path
                to a CA bundle to use.
            cert (str, optional): Defaults to None. Any user-provided SSL
                certificate to be trusted.
            proxies (dict,  optional): Defaults to None. The proxies
                dictionary to apply to the request.

        Raises:
            requests.exceptions.SSLError: if request failed due to a SSL error.
            requests.exceptions.ProxyError: if request failed due to a proxy error.
            requests.exceptions.ConnectTimeout: if request failed due to a connection timeout.
            requests.exceptions.ReadTimeout: if request failed due to a read timeout.
            requests.exceptions.ConnectionError: if there is a problem with the
                connection (default error).

        Returns:
            request.Response: the response to the request.
        """
        retries = self.max_retries

        try:
            while not retries.is_exhausted():
                try:
                    response = self._curl_send(request)

                    return response

                except RequestException as error:
                    retries = retries.increment(method=request.method, url=request.url,
                                                error=error)
                    retries.sleep()

        except MaxRetryError as retry_error:
            raise retry_error.reason

    def _curl_send(self, request, stream=False, timeout=None, verify=True, cert=None,
                   proxies=None):
        """Translates the `requests.PreparedRequest` into a CURLRequest, performs the request, and then
        translates the repsonse to a `requests.Response`, and if there is any exception, it is also translated
        into an appropiate `requests.exceptions.RequestException` subclass."""
        try:
            curl_connection = self.get_curl_connection(request.url)
            curl_request = CURLRequest(request, timeout=timeout, cert=cert, verify=verify)
            
            response = curl_connection.send(curl_request)
            
            return response.to_requests_response()
        
        except pycurl.error as curl_error:
            requests_exception = translate_curl_exception(curl_error)
            raise requests_exception("CURL error {0}".format(curl_error.args))

    def get_curl_connection(self, url):
        """Returns a new CURL connection to handle the request to a given URL.

        Args:
            url (str): the URL of the request being sent.

        Returns:
            CURLConnectionPool: a connection pool that is capable of handling the given request.
        """

        pool = self._pool_manager.get_pool_from_url(url)

        return pool

    def close(self):
        """Cleans up adapter specific items."""
        self._pool_manager.clear()
