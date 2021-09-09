INSERT OR REPLACE INTO
  user_last_notified
  (user_id, notified_timestamp)
VALUES
  (%(user_id)s, %(notified_timestamp)s)
