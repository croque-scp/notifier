SELECT
  channel,
  start_timestamp,
  end_timestamp,
  notified_user_count
FROM
  channel_log_dump
WHERE
  start_timestamp BETWEEN %(lower_timestamp)s AND %(upper_timestamp)s
