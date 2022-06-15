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
  start_timestamp BETWEEN %(lower_timestamp)s AND %(upper_timestamp)s
