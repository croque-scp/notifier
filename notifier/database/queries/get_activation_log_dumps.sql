SELECT
  start_timestamp,
  config_start_timestamp,
  config_end_timestamp,
  getpost_start_timestamp,
  getpost_end_timestamp,
  notify_start_timestamp,
  notify_end_timestamp,
  end_timestamp,

  new_post_count,
  new_thread_count,
  checked_thread_count,

  site_count,
  user_count,
  post_count,
  thread_count
FROM
  activation_log_dump
WHERE
  start_timestamp BETWEEN %(lower_timestamp)s AND %(upper_timestamp)s
