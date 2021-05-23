import pytest

from requests.exceptions import InvalidProxyURL

from requests_curl.pool_provider import CURLPoolProvider
from requests_curl.pool import CURLHandlerPool, ProxyCURLHandlerPool


def test_can_create_empty_pool_provider():
    pool_provider = CURLPoolProvider(
        max_pools=0,
        max_pool_size=10,
        pool_block=True,
    )

    assert len(pool_provider) == 0


def test_can_retrieve_a_new_pool_for_url():
    pool_provider = CURLPoolProvider(
        max_pools=10,
        max_pool_size=10,
        pool_block=True,
    )

    url = "https://someurl.io"

    handler_pool = pool_provider.get_pool_for_url(url)

    assert isinstance(handler_pool, CURLHandlerPool)

    assert len(pool_provider) == 1


def test_can_retrieve_a_new_pool_for_a_proxied_url():
    pool_provider = CURLPoolProvider(
        max_pools=10,
        max_pool_size=10,
        pool_block=True,
    )

    proxy_url = "http://localhost:8080"
    url = "https://someurl.io"

    handler_pool = pool_provider.get_pool_for_proxied_url(proxy_url, url)

    assert isinstance(handler_pool, ProxyCURLHandlerPool)
    assert handler_pool.proxy_url == proxy_url

    assert len(pool_provider) == 1


def test_provider_returns_the_same_pool_for_the_same_url():
    pool_provider = CURLPoolProvider(
        max_pools=10,
        max_pool_size=10,
        pool_block=True,
    )

    url = "https://someurl.io"

    handler_pool_1 = pool_provider.get_pool_for_url(url)
    handler_pool_2 = pool_provider.get_pool_for_url(url)

    assert handler_pool_1 is handler_pool_2

    assert len(pool_provider) == 1


def test_provider_returns_the_same_pool_for_the_same_proxied_url():
    pool_provider = CURLPoolProvider(
        max_pools=10,
        max_pool_size=10,
        pool_block=True,
    )

    proxy_url = "http://localhost:8080"
    url = "https://someurl.io"

    handler_pool_1 = pool_provider.get_pool_for_proxied_url(proxy_url, url)
    handler_pool_2 = pool_provider.get_pool_for_proxied_url(proxy_url, url)

    assert handler_pool_1 is handler_pool_2

    assert len(pool_provider) == 1


def test_provider_returns_the_same_pool_for_the_same_host():
    pool_provider = CURLPoolProvider(
        max_pools=10,
        max_pool_size=10,
        pool_block=True,
    )

    url = "https://someurl.io"
    the_same_host_url = "https://someurl.io/something"

    handler_pool_1 = pool_provider.get_pool_for_url(url)
    handler_pool_2 = pool_provider.get_pool_for_url(the_same_host_url)

    assert handler_pool_1 is handler_pool_2

    assert len(pool_provider) == 1


def test_provider_returns_the_same_pool_for_the_same_proxied_host():
    pool_provider = CURLPoolProvider(
        max_pools=10,
        max_pool_size=10,
        pool_block=True,
    )

    proxy_url = "http://localhost:8080"
    url = "https://someurl.io"
    the_same_host_url = "https://someurl.io/something"

    handler_pool_1 = pool_provider.get_pool_for_proxied_url(proxy_url, url)
    handler_pool_2 = pool_provider.get_pool_for_proxied_url(
        proxy_url, the_same_host_url
    )

    assert handler_pool_1 is handler_pool_2

    assert len(pool_provider) == 1


def test_provider_provides_different_pools_for_different_urls():
    pool_provider = CURLPoolProvider(
        max_pools=10,
        max_pool_size=10,
        pool_block=True,
    )

    url_1 = "https://someurl.io"
    url_2 = "https://adifferenturl.dev"

    handler_pool_1 = pool_provider.get_pool_for_url(url_1)
    handler_pool_2 = pool_provider.get_pool_for_url(url_2)

    assert handler_pool_1 is not handler_pool_2

    assert len(pool_provider) == 2


def test_provider_provides_different_pools_for_different_proxied_urls():
    pool_provider = CURLPoolProvider(
        max_pools=10,
        max_pool_size=10,
        pool_block=True,
    )

    proxy_url = "http://localhost:8080"
    url_1 = "https://someurl.io"
    url_2 = "https://adifferenturl.dev"

    handler_pool_1 = pool_provider.get_pool_for_proxied_url(proxy_url, url_1)
    handler_pool_2 = pool_provider.get_pool_for_proxied_url(proxy_url, url_2)

    assert handler_pool_1 is not handler_pool_2

    assert handler_pool_1.proxy_url == proxy_url
    assert handler_pool_2.proxy_url == proxy_url

    assert len(pool_provider) == 2


def test_provider_provides_different_pools_for_different_proxy_but_same_url():
    pool_provider = CURLPoolProvider(
        max_pools=10,
        max_pool_size=10,
        pool_block=True,
    )

    proxy_url_1 = "http://localhost:8080"
    proxy_url_2 = "https://localhost:8081"
    url = "https://someurl.io"

    handler_pool_1 = pool_provider.get_pool_for_proxied_url(proxy_url_1, url)
    handler_pool_2 = pool_provider.get_pool_for_proxied_url(proxy_url_2, url)

    assert handler_pool_1 is not handler_pool_2

    assert handler_pool_1.proxy_url == proxy_url_1
    assert handler_pool_2.proxy_url == proxy_url_2

    assert len(pool_provider) == 2


def test_provider_provides_different_pools_for_proxied_url_and_not_proxied_url():
    pool_provider = CURLPoolProvider(
        max_pools=10,
        max_pool_size=10,
        pool_block=True,
    )

    proxy_url = "http://localhost:8080"
    url = "https://someurl.io"

    handler_pool_1 = pool_provider.get_pool_for_proxied_url(proxy_url, url)
    handler_pool_2 = pool_provider.get_pool_for_url(url)

    assert handler_pool_1 is not handler_pool_2

    assert isinstance(handler_pool_1, ProxyCURLHandlerPool)
    assert isinstance(handler_pool_2, CURLHandlerPool)

    assert len(pool_provider) == 2


def test_clear_the_pool_provider():
    pool_provider = CURLPoolProvider(
        max_pools=10,
        max_pool_size=10,
        pool_block=True,
    )

    proxy_url = "http://localhost:8080"
    url = "https://someurl.io"

    first_handler_pool = pool_provider.get_pool_for_url(url)
    first_proxied_pool = pool_provider.get_pool_for_proxied_url(proxy_url, url)

    pool_provider.clear()

    assert len(pool_provider) == 0

    second_handler_pool = pool_provider.get_pool_for_url(url)
    second_proxied_pool = pool_provider.get_pool_for_proxied_url(proxy_url, url)

    # Since the provider was cleared, pools are different
    second_handler_pool is not first_handler_pool
    second_proxied_pool is not first_proxied_pool


def test_malformed_proxy_url_raises_invalid_proxy_url():
    pool_provider = CURLPoolProvider(
        max_pools=10,
        max_pool_size=10,
        pool_block=True,
    )

    proxy_url = "http://:8080"
    url = "https://someurl.io"

    with pytest.raises(InvalidProxyURL):
        pool_provider.get_pool_for_proxied_url(proxy_url, url)
