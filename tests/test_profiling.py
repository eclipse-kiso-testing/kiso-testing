from unittest.mock import MagicMock, patch

import pytest

from pykiso.profiling import profile


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
def test_profile_with_compression(MockVizTracer,mocker,tmp_path):
    mock_tracer = MockVizTracer.return_value.__enter__.return_value
    mock_compressor = mocker.patch("pykiso.profiling.VCompressor", autospec=True).return_value
    mock_func = MagicMock(return_value="test_result")
    mock_json = mocker.patch("json.load", return_value={"key": "value"},autospec=True)
    mock_unlink = mocker.patch("pykiso.profiling.Path.unlink")
    file_name = tmp_path / "test_result.json"

    with open(file_name, 'w+'):
        pass

    mock_open = mocker.patch("builtins.open")

    decorated_func = profile(filename=file_name.as_posix(), compress=True)(mock_func)

    result = decorated_func()

    mock_func.assert_called_once()
    mock_json.assert_called_once()
    mock_tracer.save.assert_called_once_with(file_name.as_posix())
    mock_open.assert_called_once_with(file_name.as_posix())
    mock_compressor.compress.assert_called_once()
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
def test_decorator_without_filename(MockVizTracer):
    mock_tracer = MockVizTracer.return_value.__enter__.return_value
    mock_func = MagicMock(return_value="test_result")
    mock_func.__module__ = "module_name"
    mock_func.__name__ = "function_name"
    decorated_func = profile(filename="", compress=False)(mock_func)
    result = decorated_func()

    mock_func.assert_called_once()
    mock_tracer.save.assert_called_once_with("module_name_function_name.json")
    assert result == "test_result"
