UPDATE
  user_config
SET
  user_config.frequency = "never"
WHERE
  user_config.user_id = %(user_id)s