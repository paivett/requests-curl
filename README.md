# requests-curl
[![Tests](https://github.com/paivett/requests-curl/actions/workflows/run-tests.yml/badge.svg)](https://github.com/paivett/requests-curl/actions/workflows/run-tests.yml)

This package provides an adapter to use [PyCURL](http://pycurl.io) as backend for the [requests](http://docs.python-requests.org/en/master/) library.

## Requirements

To be able to use this adapter, you need [PyCURL](http://pycurl.io), and, of course, [requests](http://docs.python-requests.org/en/master/).

## Installation

Clone this project, and then, in the desired virtualenvironment, just run

    python setup.py install

[PyPI](https://pypi.org) integration comming soon.

## Usage

Simply import the adapter and mount it

```python
import requests

from requests_curl import CURLAdapter

session = requests.Session()

session.mount("http://", CURLAdapter())
session.mount("https://", CURLAdapter())

response = session.get("https://google.com")

print(response.status_code)
```

## Running tests

Tests are implemented with pytest. To run tests, just do

    pytest tests/

### End-to-end tests
These tests are meant to test that the whole communication with a real server works. For these tests, we use docker compose and the server is based on [httpbin](http://httpbin.org/).

To run these tests, you will need Docker Compose. First, build the test runner image

```
docker-compose -f docker-compose.tests.yml build
```

Then run tests

```
docker-compose -f docker-compose.tests.yml up --exit-code-from e2e_tests_runner
```

## Release history

 * 0.1
   * Initial release

## Troubleshooting

### PyCURL
If you are having trouble installing PyCURL, check this: https://stackoverflow.com/a/51959349.

Also, if you get this error while running tests or using pycurl

```
    import pycurl
E   ImportError: pycurl: libcurl link-time ssl backends (secure-transport, openssl) do not include compile-time ssl backend (none/other)
```

On MacOS these steps worked for me:
 * Uninstall pycurl
 * Now follow the steps described here: https://github.com/transloadit/python-sdk/issues/4#issuecomment-347009356
