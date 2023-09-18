"""Helper for cached downloading and scaling of images."""


import functools
import io
import logging

import PIL.Image
import PIL.ImageTk
import requests

logger = logging.getLogger(__name__)


class HttpPhotoImageManager:
    """Helper for cached downloading of images and scaling them to the desired size."""

    _max_width: int
    _max_height: int

    def __init__(self, max_width: int, max_height: int) -> None:
        """Initializes helper for image handling.

        Args:
            max_width: Maximum width of the images returned by `get_photo_image`.
            max_height: Maximum height of the image returned by `get_photo_image`.
        """
        self._max_width = max_width
        self._max_height = max_height
        self.get_photo_image = functools.lru_cache(maxsize=1)(
            self._get_photo_image_without_caching
        )

    def _get_photo_image_without_caching(
        self, absolute_uri: str
    ) -> PIL.ImageTk.PhotoImage:
        logger.debug(
            "Creating Tkinter-compatible photo image ...",
            extra={"URI": absolute_uri},
        )
        content = _download_resource(absolute_uri)
        image = PIL.Image.open(io.BytesIO(content))
        image_wo_alpha = _remove_alpha_channel(image)
        resized_image = self._resize_image(image_wo_alpha)
        photo_image = PIL.ImageTk.PhotoImage(resized_image)
        logger.debug(
            "Tkinter-compatible photo image created.",
            extra={"URI": absolute_uri},
        )
        return photo_image

    def _resize_image(self, image: PIL.Image.Image) -> PIL.Image.Image:
        logger.debug("Resizing image ...")
        if self._max_width * image.height <= self._max_height * image.width:
            new_width = self._max_width
            new_height = round(image.height * self._max_width / image.width)
        else:
            new_width = round(image.width * self._max_height / image.height)
            new_height = self._max_height
        resized_image = image.resize(size=(new_width, new_height))
        logger.debug("Image resized.")
        return resized_image


def _download_resource(absolute_uri: str) -> bytes:
    logger.debug("Downloading resource ...", extra={"URI": absolute_uri})
    response = requests.get(absolute_uri, timeout=10)
    logger.debug("Resource downloaded.", extra={"URI": absolute_uri})
    return response.content


def _remove_alpha_channel(image: PIL.Image.Image) -> PIL.Image.Image:
    logger.debug("Removing alpha channel ...")
    if image.mode != "RGBA":
        logger.debug(
            "Cannot remove alpha channel: Image does not have an alpha channel."
        )
        return image
    rgb_image = PIL.Image.new("RGB", image.size, "white")
    rgb_image.paste(image, mask=image.getchannel("A"))
    logger.debug("Alpha channel removed.")
    return rgb_image
