from _pytest.config.argparsing import Parser
from _pytest.python import Metafunc

from notifier.config.local import read_local_config


def pytest_addoption(parser: Parser):
    parser.addoption("--notifier-config", type=str, nargs=None)


def pytest_generate_tests(metafunc: Metafunc):
    if (
        config := metafunc.config.getoption("notifier_config")
    ) and "notifier_config" in metafunc.fixturenames:
        metafunc.parametrize(
            "notifier_config", [read_local_config(config)], scope="module"
        )
