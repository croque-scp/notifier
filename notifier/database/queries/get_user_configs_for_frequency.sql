SELECT
  user_config.user_id AS user_id,
  user_config.username AS username,
  user_config.frequency AS frequency,
  user_config.language AS language,
  user_config.delivery AS delivery,
  user_config.tags AS tags,
  user_config.notified_timestamp AS last_notified_timestamp
FROM
  user_config
WHERE
  user_config.frequency = %(frequency)s
