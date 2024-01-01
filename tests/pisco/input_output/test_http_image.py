import io
import unittest.mock
from typing import Final, Literal

import faker as fk
import PIL.Image
import pytest

import pisco.input_output.http_image

Format = Literal["BMP", "GIF", "JPEG", "PNG", "TIFF"]
Mode = Literal["1", "CMYK", "F", "I", "L", "P", "RGB", "RGBA", "RGBX", "YCbCr"]

FORMAT_MODE: Final[dict[Format, list[Mode]]] = {
    "BMP": ["1", "L", "P", "RGB", "RGBA"],
    "GIF": ["1", "F", "I", "L", "P", "RGB", "RGBA"],
    "JPEG": ["1", "CMYK", "L", "RGB", "RGBX", "YCbCr"],
    "PNG": ["1", "I", "L", "P", "RGB", "RGBA"],
    "TIFF": ["1", "CMYK", "F", "I", "L", "P", "RGB", "RGBA", "RGBX"],
}

faker = fk.Faker()


def fake_image_file(
    format_: Format, mode: Mode, width: int, height: int, color: str
) -> bytes:
    bytes_io = io.BytesIO()
    image = PIL.Image.new(mode, (width, height), color=color)
    image.save(bytes_io, format=format_)
    return bytes_io.getvalue()


@pytest.mark.parametrize(
    ("format_", "mode"),
    [(format_, mode) for format_, modes in FORMAT_MODE.items() for mode in modes],
)
def test_get_photo_image_returns_correctly_scaled_image_for_http_url(
    format_: Format, mode: Mode
) -> None:
    pisco.input_output.http_image.get_photo_image.cache_clear()

    width = faker.random_int(min=10, max=500)
    height = faker.random_int(min=10, max=500)
    color = faker.safe_color_name()
    image = fake_image_file(format_, mode, width, height, color)

    uri = faker.uri(schemes=("http:", "https:"))
    max_width = faker.random_int(min=10, max=500)
    max_height = faker.random_int(min=10, max=500)

    with unittest.mock.patch(
        "pisco.input_output.http_image.urllib.request.urlopen",
        unittest.mock.mock_open(read_data=image),
    ) as mock_urlopen, unittest.mock.patch(
        "pisco.input_output.http_image.PIL.ImageTk.PhotoImage"
    ) as mock_photo_image:
        pisco.input_output.http_image.get_photo_image(uri, max_width, max_height)

    mock_urlopen.assert_called_once_with(uri, timeout=10)
    mock_photo_image.assert_called_once()

    new_width, new_height = mock_photo_image.call_args[0][0].size

    assert new_width <= max_width
    assert new_height <= max_height

    assert new_width == max_width or new_height == max_height

    if new_width < max_width:
        assert new_width == pytest.approx(new_height * width / height, abs=0.5)
    if new_height < max_height:
        assert new_height == pytest.approx(new_width * height / width, abs=0.5)


def test_get_photo_image_raises_error_for_non_http_url() -> None:
    uri = faker.uri(schemes=("file:",))
    max_width = faker.random_int(min=10, max=500)
    max_height = faker.random_int(min=10, max=500)

    with pytest.raises(
        ValueError,
        match="^Cannot download resource: URI does not start with a supported prefix.$",
    ):
        pisco.input_output.http_image.get_photo_image(uri, max_width, max_height)
