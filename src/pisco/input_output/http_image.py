"""Functions for cached downloading and scaling of images."""

import functools
import io
import logging
import urllib.request

import PIL.Image
import PIL.ImageTk

logger = logging.getLogger(__name__)


@functools.lru_cache(maxsize=1)
def get_photo_image(
    absolute_uri: str, max_width: int, max_height: int
) -> PIL.ImageTk.PhotoImage:
    """Downloads image and converts it to a Tkinter-compatible photo image.

    The image is resized so that it fits into an `max_width` x `max_height` frame
    while keeping its original aspect ratio.
    If an alpha channel is present, it is removed.

    Args:
        absolute_uri: Absolute URI of the image to download.
        max_width: Maximum width of the image.
        max_height: Maximum height of the image.

    Returns:
        Tkinter-compatible photo image with
        `width==max_width & height<=max_height` or
        `width<=max_width & height==max_height`.
    """
    logger.debug(
        "Creating Tkinter-compatible photo image ...",
        extra={"URI": absolute_uri},
    )
    content = _download_resource(absolute_uri)
    image = _to_image(content)
    image_wo_alpha = _remove_alpha_channel(image)
    resized_image = _resize_image(image_wo_alpha, max_width, max_height)
    photo_image = PIL.ImageTk.PhotoImage(
        resized_image
    )  # type: ignore[no-untyped-call] # ImageTk doesn't have type hints in Pillow 10.3.
    logger.debug(
        "Tkinter-compatible photo image created.",
        extra={"URI": absolute_uri},
    )
    return photo_image


def _download_resource(absolute_uri: str) -> bytes:
    logger.debug("Downloading resource ...", extra={"URI": absolute_uri})
    if not absolute_uri.startswith(supported_prefixes := ("http:", "https:")):
        msg = "Cannot download resource: URI does not start with a supported prefix."
        logger.debug(
            msg, extra={"supported_prefixes": supported_prefixes, "URI": absolute_uri}
        )
        raise ValueError(msg)
    with urllib.request.urlopen(absolute_uri, timeout=10) as response:  # noqa: S310
        content: bytes = response.read()
    logger.debug("Resource downloaded.", extra={"URI": absolute_uri})
    return content


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


def _resize_image(
    image: PIL.Image.Image, max_width: int, max_height: int
) -> PIL.Image.Image:
    logger.debug("Resizing image ...")
    if max_width * image.height <= max_height * image.width:
        new_width = max_width
        new_height = round(image.height * max_width / image.width)
    else:
        new_width = round(image.width * max_height / image.height)
        new_height = max_height
    resized_image = image.resize(size=(new_width, new_height))
    logger.debug("Image resized.")
    return resized_image


def _to_image(content: bytes) -> PIL.Image.Image:
    bytes_io = io.BytesIO(content)
    return PIL.Image.open(bytes_io)
