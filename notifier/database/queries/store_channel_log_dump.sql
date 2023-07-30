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
