import json
from math import inf
from typing import Any, Callable, cast

import pytest
from _pytest.monkeypatch import MonkeyPatch
from mypy_boto3_s3 import S3ServiceResource
from mypy_boto3_s3.service_resource import Object

from notifier.database.drivers.base import BaseDatabaseDriver
from notifier.dumps import record_activation_log, upload_log_dump_to_s3
from notifier.types import LocalConfig, LogDump


def construct_fake_s3_resource(
    test_func: Callable[[LogDump], None]
) -> Callable[[str], S3ServiceResource]:
    """Construct fake S3 object for monkeypatching."""

    def fake_s3_resource(_resource: str) -> S3ServiceResource:
        s3 = lambda: None
        bucket = lambda: None
        dump_object = cast(Object, lambda: None)
        setattr(s3, "Bucket", lambda _name: bucket)
        setattr(bucket, "Object", lambda _path: dump_object)

        def fake_object_put(**kwargs: Any) -> None:
            test_func(json.loads(kwargs["Body"]))

        setattr(dump_object, "put", fake_object_put)
        return cast(S3ServiceResource, s3)

    return fake_s3_resource


def test_upload_dry_run_with_no_data(
    monkeypatch: MonkeyPatch,
) -> None:
    """Test faking a log dump with no data."""

    test_func_was_called = False

    def test_func(dump: LogDump) -> None:
        assert isinstance(dump["channels"], list)
        nonlocal test_func_was_called
        test_func_was_called = True

    monkeypatch.setattr(
        "boto3.resource", construct_fake_s3_resource(test_func)
    )

    upload_log_dump_to_s3(
        "fake_bucket",
        "fake_object",
        {
            "activations": [],
            "channels": [],
        },
    )

    assert test_func_was_called


@pytest.mark.needs_database
def test_upload_dry_run_with_sample_data(
    notifier_config: LocalConfig,
    sample_database: BaseDatabaseDriver,
    monkeypatch: MonkeyPatch,
) -> None:
    """Test faking a log dump with sample data."""

    test_func_was_called = False

    def test_func(dump: LogDump) -> None:
        assert isinstance(dump["channels"], list)
        assert len(dump["channels"]) == 2
        nonlocal test_func_was_called
        test_func_was_called = True

    monkeypatch.setattr(
        "boto3.resource", construct_fake_s3_resource(test_func)
    )

    record_activation_log(notifier_config, sample_database, inf)

    assert test_func_was_called
