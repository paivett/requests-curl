import pycurl

from urllib3.poolmanager import PoolManager
from urllib3.util.queue import LifoQueue


class CURLHandlerPool(object):

    def __init__(self, url, port, maxsize=1, *args, **kwargs):
        self._block = kwargs.get("block", False)
        self._pool = LifoQueue(maxsize)

    def get_handler(self):
        # TODO: Actually keep a pool of handlerds instead of creating a new one
        return pycurl.Curl()


class CURLHandlerPoolManager(object):

    def __init__(self, initial_pool_size, max_pool_size, pool_block):
        self._poolmanager = PoolManager(num_pools=initial_pool_size, maxsize=max_pool_size,
                                        block=pool_block, strict=True)

        # Let's force the poolmanager to use our CURLHandlerPool instead of the original
        # HTTPConnectionPool
        self._poolmanager.pool_classes_by_scheme = {
            "http": CURLHandlerPool,
            "https": CURLHandlerPool,
        }

    def get_pool_from_url(self, url):
        return self._poolmanager.connection_from_url(url)

    def clear(self):
        self._poolmanager.clear()
