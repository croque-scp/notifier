from _pytest.config.argparsing import Parser
from _pytest.python import Metafunc

from notifier.config.local import read_local_auth, read_local_config


def pytest_addoption(parser: Parser) -> None:
    parser.addoption("--notifier-config", type=str, required=True)
    parser.addoption("--notifier-auth", type=str, required=True)


def pytest_generate_tests(metafunc: Metafunc) -> None:
    if (
        config := metafunc.config.getoption("notifier_config")
    ) and "notifier_config" in metafunc.fixturenames:
        metafunc.parametrize(
            "notifier_config", [read_local_config(config)], scope="module"
        )
    if (
        auth := metafunc.config.getoption("notifier_auth")
    ) and "notifier_auth" in metafunc.fixturenames:
        metafunc.parametrize(
            "notifier_auth", [read_local_auth(auth)], scope="module"
        )
