INSERT INTO
  activation_log_dump
  (
    start_timestamp,
    config_start_timestamp,
    config_end_timestamp,
    getpost_start_timestamp,
    getpost_end_timestamp,
    notify_start_timestamp,
    notify_end_timestamp,
    end_timestamp
  )
VALUES
  (
    %(start_timestamp)s,
    %(config_start_timestamp)s,
    %(config_end_timestamp)s,
    %(getpost_start_timestamp)s,
    %(getpost_end_timestamp)s,
    %(notify_start_timestamp)s,
    %(notify_end_timestamp)s,
    %(end_timestamp)s
  )
ON DUPLICATE KEY UPDATE
  config_start_timestamp = %(config_start_timestamp)s,
  config_end_timestamp = %(config_end_timestamp)s,
  getpost_start_timestamp = %(getpost_start_timestamp)s,
  getpost_end_timestamp = %(getpost_end_timestamp)s,
  notify_start_timestamp = %(notify_start_timestamp)s,
  notify_end_timestamp = %(notify_end_timestamp)s,
  end_timestamp = %(end_timestamp)s