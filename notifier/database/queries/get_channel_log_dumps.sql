SELECT
  channel,
  start_timestamp,
  end_timestamp,
  user_count,
  activated_user_count,
  notified_user_count,
  notified_post_count,
  notified_thread_count
FROM
  channel_log_dump
WHERE
  start_timestamp > %(lower_timestamp)
  AND end_timestamp < %(upper_timestamp)
