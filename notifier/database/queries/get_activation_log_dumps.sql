SELECT
  start_timestamp,
  config_start_timestamp,
  config_end_timestamp,
  getpost_start_timestamp,
  getpost_end_timestamp,
  notify_start_timestamp,
  notify_end_timestamp,
  end_timestamp
FROM
  activation_log_dump
WHERE
  start_timestamp BETWEEN %(lower_timestamp)s AND %(upper_timestamp)s
