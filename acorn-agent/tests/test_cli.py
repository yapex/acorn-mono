"""Tests for acorn-agent CLI"""
import pytest
from unittest.mock import patch, MagicMock


class TestCliCommands:
    """Test CLI command structure"""

    def test_cli_module_has_app(self):
        """CLI module should export 'app'"""
        from acorn_agent import cli
        assert hasattr(cli, "app")

    def test_cli_main_is_callable(self):
        """CLI main function should be callable"""
        from acorn_agent.cli import main
        assert callable(main)

    def test_cli_query_function_exists(self):
        """query command should be callable"""
        from acorn_agent.cli import query
        assert callable(query)

    def test_cli_list_fields_function_exists(self):
        """list_fields command should be callable"""
        from acorn_agent.cli import list_fields
        assert callable(list_fields)

    def test_cli_list_calculators_function_exists(self):
        """list_calculators command should be callable"""
        from acorn_agent.cli import list_calculators
        assert callable(list_calculators)

    def test_cli_call_function_exists(self):
        """call command should be callable"""
        from acorn_agent.cli import call
        assert callable(call)

    def test_ensure_server_running_exists(self):
        """CLI should have _ensure_server_running function"""
        from acorn_agent.cli import _ensure_server_running
        assert callable(_ensure_server_running)

    def test_start_server_background_exists(self):
        """CLI should have _start_server_background function"""
        from acorn_agent.cli import _start_server_background
        assert callable(_start_server_background)


class TestFormatter:
    """Test output formatting"""

    def test_format_value_percentage(self):
        """Percentage fields should show %"""
        from acorn_agent.formatter import _format_value
        assert _format_value(38.43, "roe") == "38.43%"

    def test_format_value_none(self):
        """None values should show N/A"""
        from acorn_agent.formatter import _format_value
        assert _format_value(None, "roe") == "N/A"

    def test_format_value_market_cap(self):
        """Market cap should be formatted in 亿"""
        from acorn_agent.formatter import _format_value
        # 10000 亿 = 1万亿
        assert _format_value(10000.0, "market_cap") == "1.00亿"

    def test_format_output_json(self):
        """JSON format should return valid JSON string"""
        from acorn_agent.formatter import _format_output
        data = {
            "data": {"roe": {2024: 38.43}},
            "fields_fetched": ["roe"]
        }
        result = _format_output(data, "json")
        import json
        parsed = json.loads(result)
        assert parsed["data"]["roe"]["2024"] == 38.43

    def test_format_output_table(self):
        """Table format should return tabulate output"""
        from acorn_agent.formatter import _format_output
        data = {
            "data": {"roe": {2024: 38.43}},
            "fields_fetched": ["roe"]
        }
        result = _format_output(data, "table")
        assert "roe" in result
        assert "38.43%" in result
        assert "2024" in result


class TestAcornClient:
    """Test RPC client"""

    def test_client_default_socket(self):
        """Client should use default socket path"""
        from acorn_agent.client import AcornClient, DEFAULT_SOCKET_PATH
        client = AcornClient()
        assert client.socket_path == str(DEFAULT_SOCKET_PATH)

    def test_client_custom_socket(self):
        """Client should accept custom socket path"""
        from acorn_agent.client import AcornClient
        client = AcornClient(socket_path="/custom/sock")
        assert client.socket_path == "/custom/sock"

    def test_client_execute_signature(self):
        """Client.execute should accept command and args"""
        from acorn_agent.client import AcornClient
        client = AcornClient()
        # Just check the method exists and has correct signature
        import inspect
        sig = inspect.signature(client.execute)
        assert "command" in sig.parameters
        assert "args" in sig.parameters
