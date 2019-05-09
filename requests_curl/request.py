import six
import pycurl

from requests.adapters import DEFAULT_CA_BUNDLE_PATH


class CURLRequest(object):
    """Representation of a request to be made using CURL."""

    

    def __init__(self, request, timeout=None, verify=None, cert=None):
        """Initializes a CURL request from a given prepared request

        Args:
            request (PreparedRequest): the prepared request comming from `requests` library.
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
        self._request = request
        self._timeout = timeout
        self._cert = cert
        self._verify = verify
        self._curl_options = None


    @property
    def use_chunked_upload(self):
        return hasattr(self._request.body, "read")

    @property
    def request(self):
        return self._request

    @property
    def options(self):
        if self._curl_options is None:
            self._curl_options = self.build_curl_options()

        return self._curl_options


    def build_curl_options(self):
        options = []

        options.append((pycurl.URL, self._request.url))
        options.append(self.build_headers_option())
        options.extend(self.build_http_method_options())
        options.extend(self.build_body_options())
        options.extend(self.build_timeout_options())
        options.extend(self.build_ca_options())
        options.extend(self.build_cert_options())

        return options


    def build_headers_option(self):
        """Returns a tuple with the pycurl option for the headers."""
        req_headers = self._request.headers.copy()
        
        if self.use_chunked_upload:
            req_headers["Transfer-Encoding"] = "chunked"

        headers = [
            "{name}: {value}".format(name=name, value=value)
            for name, value in six.iteritems(req_headers)
        ]

        return pycurl.HTTPHEADER, headers


    def build_http_method_options(self):
        method = self._request.method.upper()

        if method == "GET":
            build_options_func = self.build_get_options
        elif method == "POST":
            build_options_func = self.build_post_options
        elif method == "PUT":
            build_options_func = self.build_put_options
        elif method == "HEAD":
            build_options_func = self.build_head_options
        elif method == "OPTIONS":
            build_options_func = self.build_options_options
        elif method == "DELETE":
            build_options_func = self.build_delete_options
        elif method == "PATCH":
            build_options_func = self.build_patch_options

        return build_options_func()

    def build_get_options(self):
        return tuple()

    def build_head_options(self):
        return ((pycurl.CUSTOMREQUEST, "HEAD"),)

    def build_delete_options(self):
        return ((pycurl.CUSTOMREQUEST, "DELETE"),)

    def build_options_options(self):
            return ((pycurl.CUSTOMREQUEST, "OPTIONS"),)
    
    def build_patch_options(self):
        return ((pycurl.CUSTOMREQUEST, "PATCH"),)

    def build_put_options(self):
        return (
            (pycurl.POST, False),
            (pycurl.PUT, True),
        )

    def build_post_options(self):
        return (
            (pycurl.POST, True),
            (pycurl.PUT, False),
        )

    def build_body_options(self):
        opt, value = pycurl.NOBODY, True

        if self._request.body:
            use_chunked_upload = hasattr(self._request.body, "read")
            if use_chunked_upload:
                opt, value = pycurl.READFUNCTION, self._request.body.read
            else:
                opt, value = pycurl.POSTFIELDS, self._request.body
        
        return ((opt, value),)

    def build_timeout_options(self):
        """Returns the curl timeout options."""
        if isinstance(self._timeout, (tuple, list)):
            conn_timeout, read_timeout = self._timeout
            total_timeout = conn_timeout + read_timeout
            return (
                (pycurl.TIMEOUT_MS, int(total_timeout)),
                (pycurl.CONNECTTIMEOUT_MS, int(conn_timeout)),
            )
        elif self._timeout:
            return ((pycurl.TIMEOUT_MS, int(self._timeout)),)
        else:
            return tuple()


    def build_ca_options(self):
        """Configures the CA of this curl request."""
        if self._verify:
            ca_info = self._verify if isinstance(self._verify, six.string_types) else DEFAULT_CA_BUNDLE_PATH

            return (
                (pycurl.SSL_VERIFYHOST, 2),
                (pycurl.SSL_VERIFYPEER, 2),
                (pycurl.CAINFO, ca_info),
            )
        else:
            return (
                (pycurl.SSL_VERIFYHOST, 0),
                (pycurl.SSL_VERIFYPEER, 0)
            )

    def build_cert_options(self):
        """Configures the SSL certificate of this curl request."""

        if self._cert:
            if isinstance(self._cert, six.string_types):
                cert_path = self._cert
            else:
                cert_path, key_path = self._cert

            return (
                (pycurl.SSLCERT, cert_path),
                (pycurl.SSLKEY, key_path),
            )
        else:
            return tuple()
