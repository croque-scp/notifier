CREATE TABLE user_last_notified (
  PRIMARY KEY (user_id),
  user_id            VARCHAR(20)  NOT NULL,
  notified_timestamp INT UNSIGNED NOT NULL
);

INSERT INTO
  user_last_notified (user_id, notified_timestamp)
SELECT
  user_id, notified_timestamp
FROM
  user_config
WHERE
  notified_timestamp IS NOT NULL;

ALTER TABLE
  user_config
DROP COLUMN
  notified_timestamp;