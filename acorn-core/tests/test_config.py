"""Tests for Acorn configuration system."""
from acorn_core.config import AcornConfig, ConfigLoader


class TestConfigLoader:
    """Test configuration loading."""

    def test_load_from_nonexistent_file(self, tmp_path):
        """Test loading from non-existent file returns empty dict."""
        config_file = tmp_path / "nonexistent.toml"
        result = ConfigLoader._load_file(config_file)
        assert result == {}

    def test_load_from_valid_toml(self, tmp_path):
        """Test loading from valid TOML file."""
        config_file = tmp_path / "config.toml"
        config_file.write_text("""
[vi.query]
years = 20
wacc = 0.10

[pdf2txt.batch]
organize_by_company = true
""")
        result = ConfigLoader._load_file(config_file)
        assert result["vi"]["query"]["years"] == 20
        assert result["vi"]["query"]["wacc"] == 0.10
        assert result["pdf2txt"]["batch"]["organize_by_company"] is True

    def test_load_from_invalid_toml(self, tmp_path):
        """Test loading from invalid TOML file returns empty dict."""
        config_file = tmp_path / "config.toml"
        config_file.write_text("invalid toml {{{")
        result = ConfigLoader._load_file(config_file)
        assert result == {}


class TestAcornConfig:
    """Test AcornConfig class."""

    def test_default_values(self):
        """Test default configuration values."""
        config = AcornConfig()

        # vi.query defaults
        assert config.vi_query_years == 10
        assert config.vi_query_wacc == 0.08
        assert config.vi_query_g_terminal == 0.03

        # pdf2txt.batch defaults
        assert config.pdf2txt_batch_output_dir is None
        assert config.pdf2txt_batch_organize_by_company is False
        assert config.pdf2txt_batch_skip_existing is False

    def test_load_from_dict(self):
        """Test loading config from dictionary."""
        data = {
            "vi": {"query": {"years": 20, "wacc": 0.10}},
            "pdf2txt": {"batch": {"organize_by_company": True}}
        }
        config = AcornConfig.load_from_dict(data)

        assert config.vi_query_years == 20
        assert config.vi_query_wacc == 0.10
        assert config.vi_query_g_terminal == 0.03  # default
        assert config.pdf2txt_batch_organize_by_company is True
        assert config.pdf2txt_batch_skip_existing is False  # default

    def test_load_from_file(self, tmp_path):
        """Test loading config from file."""
        config_file = tmp_path / "config.toml"
        config_file.write_text("""
[vi.query]
years = 15
g_terminal = 0.04

[pdf2txt.batch]
skip_existing = true
""")
        config = AcornConfig.load_from_file(config_file)

        assert config.vi_query_years == 15
        assert config.vi_query_wacc == 0.08  # default
        assert config.vi_query_g_terminal == 0.04
        assert config.pdf2txt_batch_skip_existing is True

    def test_load_merges_layers(self, tmp_path):
        """Test that config layers are properly merged."""
        # Simulate merging two config sources
        base_data = {
            "vi": {"query": {"years": 10, "wacc": 0.08}}
        }
        override_data = {
            "vi": {"query": {"years": 20}}
        }

        # Merge: override takes precedence
        merged_data = {
            "vi": {
                "query": {
                    **base_data["vi"]["query"],
                    **override_data["vi"]["query"]
                }
            }
        }

        merged = AcornConfig.load_from_dict(merged_data)

        assert merged.vi_query_years == 20  # from override
        assert merged.vi_query_wacc == 0.08  # from base


class TestConfigPaths:
    """Test configuration path resolution."""

    def test_get_user_config_path(self):
        """Test user config path follows XDG spec."""
        from acorn_core.config import get_user_config_path

        path = get_user_config_path()
        assert path.name == "config.toml"
        assert "acorn" in str(path)


class TestIntegration:
    """Integration tests for configuration system."""

    def test_real_world_config(self, tmp_path):
        """Test with realistic configuration."""
        config_file = tmp_path / "config.toml"
        config_file.write_text("""
# Acorn Configuration
# Personal preferences for value investing analysis

[vi.query]
years = 20
wacc = 0.10
g_terminal = 0.03

[pdf2txt.batch]
output_dir = "./financial_reports"
organize_by_company = true
skip_existing = true
""")

        config = AcornConfig.load_from_file(config_file)

        assert config.vi_query_years == 20
        assert config.vi_query_wacc == 0.10
        assert config.vi_query_g_terminal == 0.03
        assert config.pdf2txt_batch_organize_by_company is True
        assert config.pdf2txt_batch_skip_existing is True
