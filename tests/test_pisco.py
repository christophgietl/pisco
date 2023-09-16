import pathlib


def test_pytest() -> None:
    pass


class TestBacklightManager:
    def test_activate_passes_on_dummy_backlight_manager(self) -> None:
        from pisco import BacklightManager

        backlight_manager = BacklightManager(directory=None)
        backlight_manager.activate()

    def test_activate_sets_brightness_to_max_brightness(
        self, tmp_path: pathlib.Path
    ) -> None:
        brightness_file_path = tmp_path / "brightness"
        brightness_file_path.write_text("19")
        max_brightness_file_path = tmp_path / "max_brightness"
        max_brightness_file_path.write_text("50")

        from pisco import BacklightManager

        backlight_manager = BacklightManager(directory=tmp_path)
        backlight_manager.activate()
        assert brightness_file_path.read_text() == max_brightness_file_path.read_text()

    def test_deactivate_passes_on_dummy_backlight_manager(self) -> None:
        from pisco import BacklightManager

        backlight_manager = BacklightManager(directory=None)
        backlight_manager.deactivate()

    def test_deactivate_sets_brightness_to_0(self, tmp_path: pathlib.Path) -> None:
        brightness_file_path = tmp_path / "brightness"
        brightness_file_path.write_text("19")
        max_brightness_file_path = tmp_path / "max_brightness"
        max_brightness_file_path.write_text("50")

        from pisco import BacklightManager

        backlight_manager = BacklightManager(directory=tmp_path)
        backlight_manager.deactivate()
        assert brightness_file_path.read_text() == "0"
