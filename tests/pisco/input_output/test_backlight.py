import pathlib

from pisco.input_output import backlight


class TestDummyBacklight:
    def test_activate_passes(self) -> None:
        dummy_backlight = backlight.DummyBacklight()
        dummy_backlight.activate()

    def test_deactivate_passes(self) -> None:
        dummy_backlight = backlight.DummyBacklight()
        dummy_backlight.deactivate()


class TestSysfsBacklight:
    def test_activate_sets_brightness_to_max_brightness(
        self, tmp_path: pathlib.Path
    ) -> None:
        brightness_file_path = tmp_path / "brightness"
        brightness_file_path.write_text("19")
        max_brightness_file_path = tmp_path / "max_brightness"
        max_brightness_file_path.write_text("50")

        sysfs_backlight = backlight.SysfsBacklight(directory=tmp_path)
        sysfs_backlight.activate()
        assert brightness_file_path.read_text() == "50"
        assert max_brightness_file_path.read_text() == "50"

    def test_deactivate_sets_brightness_to_zero(self, tmp_path: pathlib.Path) -> None:
        brightness_file_path = tmp_path / "brightness"
        brightness_file_path.write_text("19")
        max_brightness_file_path = tmp_path / "max_brightness"
        max_brightness_file_path.write_text("50")

        sysfs_backlight = backlight.SysfsBacklight(directory=tmp_path)
        sysfs_backlight.deactivate()
        assert brightness_file_path.read_text() == "0"
        assert max_brightness_file_path.read_text() == "50"
