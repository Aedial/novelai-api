class NovelAIError:
	status: int
	message: str

	def __init__(self, status: int, message: str) -> None:
		self.status = status
		self.message = message

	def __str__(self) -> str:
		return f"{self.status} - {self.message}"

	def __bool__(self) -> bool:
		return False