from pathlib import Path


def test_pytest():
    pass


class TestBacklight:
    def test_activate_passes_on_dummy_backlight(self):
        from pisco import Backlight
        backlight = Backlight(backlight_directory=None)
        backlight.activate()

    def test_activate_sets_brightness_to_max_brightness(self, tmp_path: Path):
        brightness_file_path = tmp_path / "brightness"
        brightness_file_path.write_text("19")
        max_brightness_file_path = tmp_path / "max_brightness"
        max_brightness_file_path.write_text("50")
        from pisco import Backlight
        backlight = Backlight(backlight_directory=str(tmp_path))
        backlight.activate()
        assert brightness_file_path.read_text() == max_brightness_file_path.read_text()

    def test_deactivate_passes_on_dummy_backlight(self):
        from pisco import Backlight
        backlight = Backlight(backlight_directory=None)
        backlight.deactivate()

    def test_deactivate_sets_brightness_to_0(self, tmp_path: Path):
        brightness_file_path = tmp_path / "brightness"
        brightness_file_path.write_text("19")
        from pisco import Backlight
        backlight = Backlight(backlight_directory=str(tmp_path))
        backlight.deactivate()
        assert brightness_file_path.read_text() == "0"


class TestHttpPhotoImageManager:
    def test_get_photo_image_maps_none_to_none(self):
        from pisco import HttpPhotoImageManager
        manager = HttpPhotoImageManager(max_width=200, max_height=200)
        assert manager.get_photo_image(None) is None
