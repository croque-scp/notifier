SELECT
  channel,
  start_timestamp,
  end_timestamp,
  user_count,
  notified_user_count,
  notified_post_count,
  notified_thread_count
FROM
  channel_log_dump
WHERE
  start_timestamp BETWEEN %(lower_timestamp)s AND %(upper_timestamp)s
