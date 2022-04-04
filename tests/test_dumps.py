import json
from math import inf
from typing import cast

import pytest
from _pytest.monkeypatch import MonkeyPatch
from mypy_boto3_s3.service_resource import Object

from dumps import upload_log_dump_to_s3
from notifier.database.drivers.base import BaseDatabaseDriver
from notifier.types import LocalConfig


@pytest.mark.usefixtures("sample_database")
def test_upload_dry_run(
    notifier_config: LocalConfig,
    sample_database: BaseDatabaseDriver,
    monkeypatch: MonkeyPatch,
):
    """Test generating a log dump and uploading it, but without actually
    touching S3."""

    def fake_object_put(**kwargs):
        assert len(json.loads(kwargs["Body"])["channels"]) == 2

    def fake_s3_resource(_resource: str):
        s3 = lambda: None
        bucket = lambda: None
        dump_object = cast(Object, lambda: None)
        setattr(s3, "Bucket", lambda _name: bucket)
        setattr(bucket, "Object", lambda _path: dump_object)
        setattr(dump_object, "put", fake_object_put)
        return s3

    monkeypatch.setattr("boto3.resource", fake_s3_resource)

    upload_log_dump_to_s3(notifier_config, sample_database, inf)
