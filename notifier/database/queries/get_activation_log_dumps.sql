SELECT
  start_timestamp,
  config_start_timestamp,
  config_end_timestamp,
  getpost_start_timestamp,
  getpost_end_timestamp,
  notify_start_timestamp,
  notify_end_timestamp,
  end_timestamp,
  sites_count,
  user_count,
  downloaded_post_count,
  downloaded_thread_count
FROM
  activation_log_dump
WHERE
  start_timestamp BETWEEN %(lower_timestamp)s AND %(upper_timestamp)s
