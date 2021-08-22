from typing import Any

class NovelAIError:
	status: Any
	message: str

	def __init__(self, status: Any, message: str) -> None:
		self.status = status
		self.message = message

	def __str__(self) -> str:
		return f"{self.status} - {self.message}"

	def __bool__(self) -> bool:
		return False