SELECT
  user_config.user_id AS user_id,
  user_config.username AS username,
  user_config.frequency AS frequency,
  user_config.language AS language,
  user_config.delivery AS delivery,
  user_last_notified.notified_timestamp AS last_notified_timestamp
FROM
  user_config
  LEFT JOIN
  user_last_notified ON user_config.user_id = user_last_notified.user_id
WHERE
  user_config.frequency = :frequency