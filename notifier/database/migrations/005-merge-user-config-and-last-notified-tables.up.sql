ALTER TABLE
  user_config
ADD COLUMN
  notified_timestamp INT UNSIGNED;

UPDATE
  user_config, user_last_notified
SET
  user_config.notified_timestamp = user_last_notified.notified_timestamp
WHERE
  user_config.user_id = user_last_notified.user_id;

DROP TABLE user_last_notified;