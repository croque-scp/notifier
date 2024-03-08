INSERT INTO
  channel_log_dump
  (
    channel,
    start_timestamp,
    end_timestamp,
    notified_user_count
  )
VALUES
  (
    %(channel)s,
    %(start_timestamp)s,
    %(end_timestamp)s,
    %(notified_user_count)s
  )
ON DUPLICATE KEY UPDATE
  end_timestamp = %(end_timestamp)s,
  notified_user_count = %(notified_user_count)s