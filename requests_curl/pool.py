import pycurl

from six.moves import queue, range
from urllib3.poolmanager import PoolManager

from .response import CURLResponse


class PoolException(Exception):
    pass


class EmptyPool(PoolException):
    pass


class ClosedPool(PoolException):
    pass


class CURLHandlerPool(object):
    """Thread-safe connection pool for one host. Tries to emulate HTTPConnectionPool."""

    def __init__(self, url, port, maxsize=1, **kwargs):
        self._block = kwargs.get("block", False)
        self._pool = queue.LifoQueue(maxsize)

        for _ in range(maxsize):
            handler = pycurl.Curl()
            self._pool.put(handler, block=False)

    def send(self, curl_request):
        """Performs a CURL request of the given CURLRequest instance, and returns
        an appropiate response.

        Args:
            curl_request (CURLRequest): an instance of a given CURL request.

        Returns:
            CURLResponse: the response of the request.

        Raises:
            pycurl.error: if there is any error while performing the request.
            EmptyPool: if there are no more connections available to perform the request.
        """

        curl_handler = self.get_handler_from_pool()

        response = CURLResponse(curl_request)

        curl_options = curl_request.options
        curl_options.extend(_get_curl_options_for_response(response))
        curl_options.extend(self.get_additional_curl_options())
        for option, value in curl_options:
            curl_handler.setopt(option, value)

        curl_handler.perform()

        response.http_code = curl_handler.getinfo(pycurl.HTTP_CODE)

        self.put_handler_back(curl_handler)

        return response

    def get_additional_curl_options(self):
        return []

    def get_handler_from_pool(self):
        """Get a CURL handler. Will return a pooled handler if one is available.

        Returns:
            pycurl.Curl: CURL handler, if available.

        Raises:
            EmptyPool: if the pool is empty and there are no more free handlers available.
        """

        try:
            curl_handler = self._pool.get(block=self._block)
            curl_handler.reset()

            return curl_handler

        except queue.Empty:
            raise EmptyPool(
                "Pool reached maximum size and no more connections are allowed."
            )

        except AttributeError:
            raise ClosedPool("Pool is no longer available")

    def put_handler_back(self, curl_handler):
        """Put a curl handler back into the pool.

        Args:
            curl_handler (pycurl.Curl:): the handler to put back into the pool.
        """
        try:
            self._pool.put(curl_handler, block=False)

        except AttributeError:
            pass  # Pool was closed

    def close(self):
        """Close all pooled connections and disable the pool."""
        # This is almost identical to the HTTPConnectionPool.close implementation

        if self._pool is None:
            return

        # Disable access to the pool
        old_pool, self.pool = self.pool, None

        try:
            while True:
                curl_handler = old_pool.get(block=False)
                curl_handler.close()

        except queue.Empty:
            pass  # Done.


class ProxyCURLHandlerPool(CURLHandlerPool):
    def __init__(self, proxy_url, url, port, maxsize=1, **kwargs):
        super(ProxyCURLHandlerPool, self).__init__(url, port, maxsize=maxsize, **kwargs)

        self._proxy_url = proxy_url

    def get_additional_curl_options(self):
        options = [
            (pycurl.PROXY, self._proxy_url.host),
            (pycurl.PROXYAUTH, pycurl.HTTPAUTH_ANY),
            (pycurl.PROXYUSERPWD, self._proxy_url.auth),
        ]

        if self._proxy_url.port:
            options.append((pycurl.PROXYPORT, self._proxy_url.port))

        return options


def _get_curl_options_for_response(response):
    return (
        (pycurl.HEADERFUNCTION, response.parse_header_line),
        (pycurl.WRITEFUNCTION, response.body.write),
    )


class CURLHandlerPoolManager(object):
    def __init__(self, initial_pool_size, max_pool_size, pool_block, pool_constructor):
        self._poolmanager = PoolManager(
            num_pools=initial_pool_size,
            maxsize=max_pool_size,
            block=pool_block,
            strict=True,
        )

        # Let's force the poolmanager to use our CURLHandlerPool instead of the original
        # HTTPConnectionPool
        self._poolmanager.pool_classes_by_scheme = {
            "http": pool_constructor,
            "https": pool_constructor,
        }

    def get_pool_from_url(self, url):
        """Returns an instance of a CURLHandlerPool for a given URL"""
        return self._poolmanager.connection_from_url(url)

    def clear(self):
        self._poolmanager.clear()
