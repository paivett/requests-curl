"""Requests adapter implementing a CURL backend"""

import six
import pycurl

from requests.exceptions import RequestException
from requests.structures import CaseInsensitiveDict
from requests.utils import get_encoding_from_headers
from requests.cookies import extract_cookies_to_jar
from requests.adapters import (
    BaseAdapter, DEFAULT_CA_BUNDLE_PATH, DEFAULT_RETRIES,
    DEFAULT_POOLSIZE, DEFAULT_POOLBLOCK
)
from requests import Response as RequestResponse
from urllib3.util.retry import Retry
from urllib3.exceptions import MaxRetryError
from urllib3.response import HTTPResponse as URLLib3Rresponse

from .pool import CURLHandlerPoolManager
from .error import translate_curl_exception


class CURLRequest(object):
    """Implementation of a request using PyCURL."""

    def __init__(self, curl_handler=None):
        # The handler is exposed so that subclasses can use it.
        if curl_handler:
            self.curl_handler = curl_handler
        else:
            self.curl_handler = pycurl.Curl()

        self._response_headers = {}
        self._response_reason = None

    def _reset(self):
        """Resets internal state of the request, leaving it ready for a new
        request.
        """

        self.curl_handler.reset()
        self._response_headers = {}

    def _configure(self, request, stream=False, timeout=None, verify=True,
                   cert=None):
        """Configures the internal state of the curl request, leaving the instance
        ready to perform the request itself. Any previous configured state
        will be reseted.

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
        """

        self._reset()

        # Perform some default curl configuration
        self.curl_handler.setopt(pycurl.HEADERFUNCTION,
                                 self.parse_header_line)
        self.curl_handler.setopt(pycurl.URL, request.url)

        self.configure_headers(request)
        self.configure_timeout(timeout)
        self.configure_cert(cert)
        self.configure_ca(verify)

        # Finally, configure the appropiate method
        method = request.method.upper()

        configure_functions = {
            "GET": self.configure_method_get,
            "HEAD": self.configure_method_head,
            "DELETE": self.configure_method_delete,
            "OPTIONS": self.configure_method_options,
        }

        configure_method_func = configure_functions.get(request.method)
        if configure_method_func:
            configure_method_func(request)
        else:
            raise RuntimeError("Method '{0}' not supported".format(method))

    def configure_method_get(self, request):
        """Configure the current request instance for a GET

        Note:
            This should not be called from user code. It is exposed to be
            subclassed only.
        """
        # Do nothing, since for a GET, we need to configure nothing, it
        # is the default behaviour
        pass

    def configure_method_delete(self, request):
        """Configure the current request instance for a DELETE

        Note:
            This should not be called from user code. It is exposed to be
            subclassed only.
        """
        self.curl_handler.setopt(pycurl.CUSTOMREQUEST, "DELETE")

    def configure_method_head(self, request):
        """Configure the current request instance for a HEAD

        Note:
            This should not be called from user code. It is exposed to be
            subclassed only.
        """
        self.curl_handler.setopt(pycurl.CUSTOMREQUEST, "HEAD")
        self.curl_handler.setopt(pycurl.NOBODY, True)

    def configure_method_options(self, request):
        """Configure the current request instance for a OPTIONS

        Note:
            This should not be called from user code. It is exposed to be
            subclassed only.
        """
        self.curl_handler.setopt(pycurl.CUSTOMREQUEST, "OPTIONS")
        self.curl_handler.setopt(pycurl.NOBODY, True)

    def configure_headers(self, request):
        """Configures the request headers.

        Args:
            request (PreparedRequest): the request being sent.
        """
        headers = [
            "{name}: {value}".format(name=name, value=value)
            for name, value in six.iteritems(request.headers)
        ]

        self.curl_handler.setopt(pycurl.HTTPHEADER, headers)

    def configure_timeout(self, timeout=None):
        """Configures the timeout of this curl request.

        Note:
            This should not be called from user code. It is exposed to be
            subclassed only.

        Args:
            timeout (float, optional): Defaults to None. How long to wait for
                the server to send data before giving up, as a float, or a
                `(connect timeout, read timeout)` tuple.
        """
        if isinstance(timeout, (tuple, list)):
            conn_timeout, read_timeout = timeout
            total_timeout = conn_timeout + read_timeout
            self.curl_handler.setopt(pycurl.TIMEOUT_MS, int(total_timeout))
            self.curl_handler.setopt(pycurl.CONNECTTIMEOUT_MS, int(conn_timeout))
        elif timeout:
            self.curl_handler.setopt(pycurl.TIMEOUT_MS, int(timeout))

    def configure_ca(self, verify=True):
        """Configures the timeout of this curl request.

        Note:
            This should not be called from user code. It is exposed to be
            subclassed only.

        Args:
            verify (bool, optional): Defaults to True. Either a boolean, in
                which case it controls whether we verify the server's TLS
                certificate, or a string, in which case it must be a path
                to a CA bundle to use.
        """
        if verify:
            self.curl_handler.setopt(pycurl.SSL_VERIFYHOST, 2)
            self.curl_handler.setopt(pycurl.SSL_VERIFYPEER, 2)

            ca_info = verify if isinstance(verify, six.string_types) else DEFAULT_CA_BUNDLE_PATH

            self.curl_handler.setopt(pycurl.CAINFO, ca_info)
        else:
            self.curl_handler.setopt(pycurl.SSL_VERIFYHOST, 0)
            self.curl_handler.setopt(pycurl.SSL_VERIFYPEER, 0)

    def configure_cert(self, cert=None):
        """Configures the timeout of this curl request.

        Args:
            cert (str, optional): Defaults to None. Any user-provided SSL
                certificate to be trusted.
        """

        if cert:
            if isinstance(cert, six.string_types):
                cert_path = cert
            else:
                cert_path, key_path = cert

            self.curl_handler.setopt(pycurl.SSLCERT, cert_path)
            self.curl_handler.setopt(pycurl.SSLKEY, key_path)

    def send(self, request, stream=False, timeout=None, verify=True,
             cert=None):
        """Performs the request using PyCURL, and upon success, returns a
        requests.Response instance. If there is an error, then the error
        generated by PyCURL will be translated to the most suitable
        requests exception.

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

        Raises:
            requests.exceptions.SSLError: if request failed due to a SSL error.

        Returns:
            request.Response: the response to the request.
        """

        try:
            self._configure(request)

            body = self.curl_handler.perform_rb()

            response = self._create_requests_response(request,
                                                      six.BytesIO(body))

            return response
        except pycurl.error as curl_error:
            requests_exception = translate_curl_exception(curl_error)

            raise requests_exception("CURL error {0}".format(curl_error.args))

    def parse_header_line(self, header_line):
        """This method is the callback configured to parse each line of
        the response headers.

        Note:
            This should not be called from user code. It is exposed to be
            subclassed only.

        Args:
            header_line (str): a line of the headers section.
        """

        # HTTP standard specifies that headers are encoded in iso-8859-1.
        header_line = header_line.decode('iso-8859-1')

        # Header lines include the first status line (HTTP/1.x ...).
        # We are going to ignore all lines that don't have a colon in them.
        # This will botch headers that are split on multiple lines...
        if ':' not in header_line:
            return

        name, value = header_line.split(':', 1)
        self.add_response_header(name.strip(), value.strip())

    def add_response_header(self, name, value):
        """Adds a response header value to the internal response headers.

        Note:
            This should not be called from user code. It is exposed to be
            subclassed only.

        Args:
            name ([type]): [description]
            value ([type]): [description]
        """

        self._response_headers[name] = value

    def _create_requests_response(self, request, body):
        """Creates a requests.Response instance to be returned after a curl request.

        Args:
            request ([type]): [description]
            body ([type]): [description]

        Returns:
            request.Response: the generated response.
        """

        urllib3_response = URLLib3Rresponse(
            body=body,
            headers=self._response_headers,
            status=self.curl_handler.getinfo(pycurl.HTTP_CODE),
            request_method=request.method,
            reason=self._response_reason,
            preload_content=False
        )

        response = RequestResponse()
        response.request = request
        response.raw = urllib3_response
        response.status_code = response.raw.status
        response.reason = response.raw.reason
        response.headers = CaseInsensitiveDict(response.raw.headers)
        response.encoding = get_encoding_from_headers(response.headers)

        extract_cookies_to_jar(response.cookies,
                               request,
                               urllib3_response)

        if isinstance(request.url, six.binary_type):
            response.url = request.url.decode("utf-8")
        else:
            response.url = request.url

        return response


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
        """
        curl_request = self.get_curl_request(request)

        retries = self.max_retries

        try:
            while not retries.is_exhausted():
                try:
                    response = curl_request.send(request, stream=stream, timeout=timeout,
                                                 verify=verify, cert=cert)
                    return response
                except RequestException as error:
                    retries = retries.increment(method=request.method, url=request.url,
                                                error=error)
                    retries.sleep()
        except MaxRetryError as retry_error:
            raise retry_error.reason

    def get_curl_request(self, request):
        """Creates a new CURLRequests based on the given request.

        Args:
            request (PreparedRequest): the request being sent.

        Returns:
            CURLRequest: the new CURL-based request.
        """

        pool = self._pool_manager.get_pool_from_url(request.url)

        return CURLRequest(pool.get_handler())

    def close(self):
        """Cleans up adapter specific items."""
        self._pool_manager.clear()
