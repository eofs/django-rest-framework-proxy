import socket

from requests.adapters import HTTPAdapter
from requests.packages.urllib3.response import HTTPResponse
from requests.packages.urllib3.exceptions import MaxRetryError
from requests.packages.urllib3.exceptions import TimeoutError
from requests.packages.urllib3.exceptions import SSLError as _SSLError
from requests.packages.urllib3.exceptions import HTTPError as _HTTPError
from requests.exceptions import ConnectionError, Timeout, SSLError


class StreamingHTTPAdapter(HTTPAdapter):
    def send(self, request, stream=False, timeout=None, verify=True, cert=None, proxies=None):
        """Stream PreparedRequest object. Returns Response object."""

        conn = self.get_connection(request.url, proxies)

        self.cert_verify(conn, request.url, verify, cert)
        url = self.request_url(request, proxies)

        try:
            if hasattr(conn, 'proxy_pool'):
                conn = conn.proxy_pool

            low_conn = conn._get_conn(timeout=timeout)
            low_conn.putrequest(request.method, url, skip_accept_encoding=True)

            for header, value in request.headers.items():
                low_conn.putheader(header, value)

            low_conn.endheaders()

            for i in request.body:
                low_conn.send(i)

            r = low_conn.getresponse()
            resp = HTTPResponse.from_httplib(r,
                pool=conn,
                connection=low_conn,
                preload_content=False,
                decode_content=False
            )

        except socket.error as sockerr:
            raise ConnectionError(sockerr)

        except MaxRetryError as e:
            raise ConnectionError(e)

        except (_SSLError, _HTTPError) as e:
            if isinstance(e, _SSLError):
                raise SSLError(e)
            elif isinstance(e, TimeoutError):
                raise Timeout(e)
            else:
                raise Timeout('Request timed out.')

        r = self.build_response(request, resp)

        if not stream:
            r.content

        return r
