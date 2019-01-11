"""Requests adapter implementing a CURL backend"""

import requests
import pycurl

from urllib3.util.retry import Retry


DEFAULT_RETRIES = 3


class CURLAdapter(requests.adapters.BaseAdapter):
    """A requests adapter implemented using PyCURL"""

    def __init__(self, max_retries=DEFAULT_RETRIES):
        super(CURLAdapter, self).__init__()

        if max_retries == DEFAULT_RETRIES:
            self.max_retries = Retry(0, read=False)
        else:
            self.max_retries = Retry.from_int(max_retries)

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
        raise NotImplementedError

    def close(self):
        """Cleans up adapter specific items."""
        raise NotImplementedError
