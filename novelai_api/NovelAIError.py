from typing import Any

class NovelAIError:
	status: int
	message: Any

	def __init__(self, status: int, message: Any) -> None:
		self.status = status
		self.message = message

	def __str__(self) -> str:
		return f"{self.status} - {self.message}"

	def __bool__(self) -> bool:
		return False