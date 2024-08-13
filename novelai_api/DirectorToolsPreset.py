import base64
import enum
import io
from pathlib import Path
from typing import Any, Dict, Union

from PIL import Image


class RequestType(enum.Enum):
    """Enum for the type of request."""

    BG_REMOVAL = "bg-removal"
    LINE_ART = "lineart"
    SKETCH = "sketch"
    COLORIZE = "colorize"
    EMOTION = "emotion"
    DECLUTTER = "declutter"


class DirectorToolsPreset:
    """Class for Director Tools Preset."""

    #: Height of the image.
    height: int
    #: Width of the image.
    width: int
    #: Image encoded in base64.
    image: str
    #: Reduce the impact of the tool (higher = less change in colorize or emotion).
    defry: int
    #: Prompt for the tool. Only used for colorize and emotion.
    prompt: str
    #: Emotion for the tool. Only used for emotion.
    emotion: str

    def __init__(
        self,
        height: int,
        width: int,
        image: str,
        defry: int = 0,
        prompt: str = "",
        emotion: str = "",
    ):
        """
        Initialize the object.

        :param height: Height of the image.
        :param width: Width of the image.
        :param image: Image encoded in base64.
        :param defry: Reduce the impact of the tool (higher = less change in colorize or emotion).
        :param prompt: Prompt for the tool. Only used for colorize and emotion.
        :param emotion: Emotion for the tool. Only used for emotion.
        """

        self.height = height
        self.width = width
        self.image = image
        self.defry = defry
        self.prompt = prompt
        self.emotion = emotion

    def load_image_from(self, image: Union[Path, bytes]):
        """
        Load the image from a file or raw data:

        :param image: Path to the image file or raw image data.
        """

        if isinstance(image, Path):
            image = image.read_bytes()

        if not isinstance(image, bytes):
            raise ValueError("Invalid image data. Expected bytes or Path object.")

        self.image = base64.b64encode(image).decode("utf-8")
        img = Image.open(io.BytesIO(image))
        self.width, self.height = img.size

    @classmethod
    def from_image(cls, image: Union[Path, bytes]) -> "DirectorToolsPreset":
        """
        Create a new object from an image.

        :param image: Path to the image file or raw image data.
        """

        obj = cls(0, 0, "")
        obj.load_image_from(image)

        return obj

    def to_settings(self, request_type: RequestType) -> Dict[str, Any]:
        """
        Convert the object to a dictionary.
        """

        if self.height < 1 or self.width < 1 or not self.image:
            raise ValueError(f"Invalid image data. Height: {self.height}, Width: {self.width}, Image: {self.image}")

        args = {
            "height": self.height,
            "width": self.width,
            "image": self.image,
            "req_type": request_type.value,
        }

        if request_type in (RequestType.COLORIZE, RequestType.EMOTION):
            args["defry"] = self.defry

            if request_type == RequestType.EMOTION:
                prompt = f"{self.emotion};;{self.prompt}"
            else:
                prompt = self.prompt

            args["prompt"] = prompt

        return args

    # TODO: add cost calculation
