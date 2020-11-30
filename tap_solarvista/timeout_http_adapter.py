""" TimeoutHttpAdapter is responsible for timeout of requests to Solarvista API """
from requests.adapters import HTTPAdapter

DEFAULT_TIMEOUT = 15 # seconds

class TimeoutHttpAdapter(HTTPAdapter):
    """ Timeout HTTP requests """

    def __init__(self, *args, **kwargs):
        """ Constructor with configurable timeout and http adapter """
        self.timeout = DEFAULT_TIMEOUT
        if "timeout" in kwargs:
            self.timeout = kwargs["timeout"]
            del kwargs["timeout"]
        super().__init__(*args, **kwargs)

    #pylint: disable=arguments-differ
    def send(self, request, **kwargs):
        timeout = kwargs.get("timeout")
        if timeout is None:
            kwargs["timeout"] = self.timeout
        return super().send(request, **kwargs)
