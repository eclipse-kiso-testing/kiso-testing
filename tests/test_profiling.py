import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from pykiso.profiling import profile


@pytest.fixture
def MockVizTracer():
    with patch('pykiso.profiling.VizTracer') as mock:
        yield mock

@patch('pykiso.profiling.VizTracer')
def test_profile_without_compression(MockVizTracer):
    mock_tracer = MockVizTracer.return_value.__enter__.return_value
    mock_func = MagicMock(return_value="test_result")

    decorated_func = profile(filename="test_result.json", compress=False)(mock_func)
    result = decorated_func()

    mock_func.assert_called_once()
    mock_tracer.save.assert_called_once_with("test_result.json")
    assert result == "test_result"

@patch('pykiso.profiling.VizTracer')
@patch('pykiso.profiling.VCompressor')
@patch('pykiso.profiling.Path.unlink')
def test_profile_with_compression(mocker,mock_unlink, MockVCompressor, MockVizTracer,tmp_path):
    mock_open = mocker.patch("builtins.open")
    mock_tracer = MockVizTracer.return_value.__enter__.return_value
    mock_compressor = MockVCompressor.return_value
    mock_func = MagicMock(return_value="test_result")

    file_name = tmp_path / "test_result.json"
    decorated_func = profile(filename=file_name.as_posix(), compress=True)(mock_func)

    result = decorated_func()

    mock_func.assert_called_once()
    mock_tracer.save.assert_called_once_with("test_result.json")
    mock_open.assert_called_once_with("test_result.json")
    mock_compressor.compress.assert_called_once_with({"key": "value"}, "test_result.cvf")
    mock_unlink.assert_called_once()
    assert result == "test_result"

@patch('pykiso.profiling.VizTracer')
def test_profile_without_filename(MockVizTracer):
    mock_tracer = MockVizTracer.return_value.__enter__.return_value
    mock_func = MagicMock(return_value="test_result")

    decorated_func = profile(filename=None, compress=False)(mock_func)
    result = decorated_func()

    mock_func.assert_called_once()
    mock_tracer.save.assert_not_called()
    assert result == "test_result"

@patch('pykiso.profiling.VizTracer')
def test_profile_with_different_filename(MockVizTracer):
    mock_tracer = MockVizTracer.return_value.__enter__.return_value
    mock_func = MagicMock(return_value="test_result")

    decorated_func = profile(filename="different_result.json", compress=False)(mock_func)
    result = decorated_func()

    mock_func.assert_called_once()
    mock_tracer.save.assert_called_once_with("different_result.json")
    assert result == "test_result"

@patch('pykiso.profiling.VizTracer')
@patch('pykiso.profiling.VCompressor')
@patch('pykiso.profiling.Path.unlink')
def test_profile_with_empty_data(mocker, mock_unlink, MockVCompressor, MockVizTracer):
    mock_open = mocker.patch("builtins.open")
    mock_tracer = MockVizTracer.return_value.__enter__.return_value
    mock_compressor = MockVCompressor.return_value
    mock_func = MagicMock(return_value="test_result")

    decorated_func = profile(filename="test_result.json", compress=True)(mock_func)
    result = decorated_func()

    mock_func.assert_called_once()
    mock_tracer.save.assert_called_once_with("test_result.json")
    mock_open.assert_called_once_with("test_result.json")
    mock_compressor.compress.assert_called_once_with({"key": "value"}, "test_result.cvf")
    mock_unlink.assert_called_once()
    assert result == "test_result"
