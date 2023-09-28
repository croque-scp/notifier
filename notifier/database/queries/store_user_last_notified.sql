UPDATE
  user_config
SET
  user_config.notified_timestamp = %(notified_timestamp)s
WHERE
  user_config.user_id = %(user_id)s