import six

from requests import Response as RequestResponse
from requests.utils import get_encoding_from_headers
from requests.structures import CaseInsensitiveDict
from requests.cookies import extract_cookies_to_jar
from urllib3.response import HTTPResponse as URLLib3Rresponse


class CURLResponse(object):
    """This class represents a CURL response"""

    def __init__(self, curl_request):
        """Initializes a new response object.

        Args:
            curl_request (CURLRequest): the request that originated this response.
        """

        self.curl_request = curl_request
        self.request = curl_request.request
        self.headers = dict()
        self.body = six.BytesIO()
        self.reason = None
        self.http_code = None

    def to_requests_response(self):
        """Returns an instance of `requests.Response` based on this response.

        Returns:
            request.Response: the generated response.
        """

        # Make sure that body is at position 0 before returning
        self.body.seek(0)

        urllib3_response = URLLib3Rresponse(
            body=self.body,
            headers=self.headers,
            status=self.http_code,
            request_method=self.request.method,
            reason=self.reason,
            preload_content=False,
        )

        response = RequestResponse()
        response.request = self.request
        response.raw = urllib3_response
        response.status_code = self.http_code
        response.reason = self.reason
        response.headers = CaseInsensitiveDict(response.raw.headers)
        response.encoding = get_encoding_from_headers(response.headers)

        extract_cookies_to_jar(response.cookies, self.request, urllib3_response)

        if isinstance(self.request.url, six.binary_type):
            response.url = self.request.url.decode("utf-8")
        else:
            response.url = self.request.url

        return response

    def parse_header_line(self, header_line):
        """This method is to be used as a callback to configure pycurl.HEADERFUNCTION
        option, which parses each line of the response headers.

        Args:
            str: a line of the headers section.
        """

        # HTTP standard specifies that headers are encoded in iso-8859-1.
        header_line = header_line.decode("iso-8859-1")

        # Header lines include the first status line (HTTP/1.x ...).
        # We are going to ignore all lines that don't have a colon in them.
        # This will botch headers that are split on multiple lines...
        if ":" not in header_line:
            return

        name, value = header_line.split(":", 1)
        self.headers[name.strip()] = value.strip()
