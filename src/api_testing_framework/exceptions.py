class APIError(Exception):
    """Raised when an API call returns a non-2xx status."""

    def __init__(self, status_code: int, message: str, response: dict):
        super().__init__(f"{status_code} Error: {message}")
        self.status_code = status_code
        self.response = response
