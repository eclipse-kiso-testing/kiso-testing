import pickle
from collections import OrderedDict


def serialize_step_report(step_report: OrderedDict, filename: str):
    """Serialize a step report to a pickle file.
    :param step_report: The step report data to be serialized. Must be an instance of OrderedDict.
    :param filename: The path to the file where the serialized data will be saved.

    :return: None
    """
    if not isinstance(step_report, OrderedDict):
        raise TypeError("step_report must be an OrderedDict")

    with open(filename, "wb") as f:
        pickle.dump(step_report, f, protocol=pickle.HIGHEST_PROTOCOL)
        print(f"Step report saved in: {filename}")


def deserialize_step_report(filename: str) -> OrderedDict:
    """Deserialize a pickle file to an OrderedDict containing the step report.
    :param filename: The path to the pickle file to be deserialized.

    :return: An OrderedDict containing the deserialized step report.
    """
    with open(filename, "rb") as f:
        return pickle.load(f)
