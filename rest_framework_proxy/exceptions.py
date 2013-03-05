class ProxyException(Exception):
    pass

class ProxyRequestException(Exception):
    def __init__(self, status_code, reason):
        self.status_code = status_code
        self.reason = reason

    def __str__(self):
        return '[%d] %s' % (self.status_code, self.reason)
