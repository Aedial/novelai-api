class NovelAIError(Exception):
    """
    Expected raised by the NAI API when a problem occurs
    """

    #: Url that caused the error
    url: str
    #: Provided status code, or -1 if no status code was provided
    status: int
    #: Provided error message
    message: str

    def __init__(self, url: str, status: int, message: str) -> None:
        self.url = url
        self.status = status
        self.message = message

    def __str__(self) -> str:
        return f"{self.url} ({self.status}) - {self.message}"
