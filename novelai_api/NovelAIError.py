class NovelAIError(Exception):
    """
    Expected raised by the NAI API when a problem occurs
    """

    #: Provided status code, or -1 if no status code was provided
    status: int
    #: Provided error message
    message: str

    def __init__(self, status: int, message: str) -> None:
        self.status = status
        self.message = message

    def __str__(self) -> str:
        return f"{self.status} - {self.message}"
