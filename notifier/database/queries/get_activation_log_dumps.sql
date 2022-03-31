SELECT
  start_timestamp,
  end_timestamp,
  sites_count,
  user_count,
  downloaded_post_count,
  downloaded_thread_count
FROM
  activation_log_dump
WHERE
  start_timestamp > %(lower_timestamp)
  AND end_timestamp < %(upper_timestamp)
