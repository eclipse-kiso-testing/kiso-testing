import os
import pickle
from collections import OrderedDict

import pytest

from pykiso.test_result.serialize_step_report import deserialize_step_report, serialize_step_report


@pytest.fixture
def sample_step_report():
    """Fixture to provide a sample OrderedDict step report."""
    return OrderedDict([("step1", "passed"), ("step2", "failed"), ("step3", "skipped")])


@pytest.fixture
def temp_file(tmp_path):
    """Fixture to provide a temporary file for testing."""
    return tmp_path / "test_step_report.pkl"


def test_serialize_step_report(sample_step_report, temp_file):
    """Test the serialize_step_report function."""
    serialize_step_report(sample_step_report, temp_file)

    # Verify the file is created
    assert os.path.exists(temp_file)

    # Verify the content of the file
    with open(temp_file, "rb") as f:
        data = pickle.load(f)
    assert data == sample_step_report


def test_deserialize_step_report(sample_step_report, temp_file):
    """Test the deserialize_step_report function."""
    # Serialize the sample step report first
    with open(temp_file, "wb") as f:
        pickle.dump(sample_step_report, f, protocol=pickle.HIGHEST_PROTOCOL)

    # Deserialize and verify the content
    deserialized_data = deserialize_step_report(temp_file)
    assert deserialized_data == sample_step_report


def test_serialize_and_deserialize_step_report(sample_step_report, temp_file):
    """Test the integration of serialize_step_report and deserialize_step_report."""
    serialize_step_report(sample_step_report, temp_file)
    deserialized_data = deserialize_step_report(temp_file)

    # Verify the deserialized data matches the original
    assert deserialized_data == sample_step_report


def test_serialize_step_report_invalid_filename(sample_step_report):
    """Test serialize_step_report with an invalid filename."""
    with pytest.raises(OSError):
        serialize_step_report(sample_step_report, "/invalid/path/test.pkl")


def test_serialize_step_report_invalid_data_type(temp_file):
    """Test serialize_step_report with an invalid data type."""
    invalid_data = ["step1", "passed", "step2", "failed"]  # Not an OrderedDict
    with pytest.raises(TypeError):
        serialize_step_report(invalid_data, temp_file)
