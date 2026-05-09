import yaml

from mcp_server.patch_settings import patch_settings


class TestPatchSettings:
    def test_file_not_exists(self, tmp_path):
        patch_settings(str(tmp_path / "nonexistent.yml"))

    def test_adds_json_format(self, tmp_path):
        settings_file = tmp_path / "settings.yml"
        settings_file.write_text(yaml.dump({"search": {"formats": ["html"]}}))

        patch_settings(str(settings_file))

        result = yaml.safe_load(settings_file.read_text())
        assert "json" in result["search"]["formats"]
        assert "html" in result["search"]["formats"]

    def test_already_has_json(self, tmp_path):
        settings_file = tmp_path / "settings.yml"
        original = {"search": {"formats": ["html", "json"]}}
        settings_file.write_text(yaml.dump(original))
        mtime_before = settings_file.stat().st_mtime

        patch_settings(str(settings_file))

        assert settings_file.stat().st_mtime == mtime_before

    def test_empty_file(self, tmp_path):
        settings_file = tmp_path / "settings.yml"
        settings_file.write_text("")

        patch_settings(str(settings_file))

        result = yaml.safe_load(settings_file.read_text())
        assert "json" in result["search"]["formats"]

    def test_no_search_section(self, tmp_path):
        settings_file = tmp_path / "settings.yml"
        settings_file.write_text(yaml.dump({"server": {"port": 8080}}))

        patch_settings(str(settings_file))

        result = yaml.safe_load(settings_file.read_text())
        assert "json" in result["search"]["formats"]
