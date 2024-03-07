from dataclasses import dataclass
import json
import logging
import time
from datetime import datetime
from typing import Callable, Generic, TypeVar

import boto3
from dateutil import tz

from notifier.database.drivers.base import BaseDatabaseDriver
from notifier.types import (
    ActivationLogDump,
    ChannelLogDump,
    LocalConfig,
    LogDump,
)

logger = logging.getLogger(__name__)

HALF_AN_HOUR_S = 60 * 30
ONE_DAY_S = 60 * 60 * 24
ENTRY_RETAIN_LIMIT = ONE_DAY_S * 31 * 3


AnyLogDump = TypeVar("AnyLogDump", ChannelLogDump, ActivationLogDump)


@dataclass
class LogDumpCacher(Generic[AnyLogDump]):
    """Wrapper for caching a log dump only when not doing a dry run."""

    data: AnyLogDump
    cache_func: Callable[[AnyLogDump], None]
    dry_run: bool

    def update(self, data: AnyLogDump) -> None:
        """Adds the given key to the log dump and caches it if not a dry run."""
        self.data.update(data)
        if not self.dry_run:
            self.cache_func(self.data)


def record_activation_log(
    config: LocalConfig,
    database: BaseDatabaseDriver,
    entry_retain_limit: float = ENTRY_RETAIN_LIMIT,
) -> None:
    """Records and uploads a notifier activation log."""

    logger.debug("Constructing log dump")

    # Construct a log dump from the database
    now = int(time.time())
    timestamp_range = (
        # Add a half hour to the limit to cover any run discrepancies
        # Also handle case where the limit is set to math.inf
        int(max(0, now - (entry_retain_limit + HALF_AN_HOUR_S))),
        now,
    )
    dump = database.get_log_dumps_since(timestamp_range)

    logger.debug(
        "Constructed log dump %s",
        {
            "activation_count": len(dump["activations"]),
            "channel_count": len(dump["channels"]),
            "timestamp_range": timestamp_range,
        },
    )

    upload_log_dump_to_s3(
        config["log_dump_s3"]["bucket_name"],
        config["log_dump_s3"]["object_key"],
        dump,
    )


def upload_log_dump_to_s3(
    bucket_name: str,
    object_key: str,
    dump: LogDump,
) -> None:
    """Uploads an aggregated log dump."""
    # Acquire the dump object from S3
    dump_object = boto3.resource("s3").Bucket(bucket_name).Object(object_key)

    # The Expires header should be set to the end of the current hour
    expiry = datetime.now(tz=tz.gettz("GMT"))
    expiry = expiry.replace(minute=59, second=59, microsecond=0)

    # Upload
    logger.debug(
        "Uploading log dump %s",
        {
            "activation_count": len(dump["activations"]),
            "channel_count": len(dump["channels"]),
            "expires": expiry,
        },
    )
    dump_object.put(
        Body=json.dumps(dump).encode("utf-8"),
        ContentType="application/json",
        Expires=expiry,
    )
