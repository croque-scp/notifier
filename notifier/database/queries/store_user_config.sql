INSERT INTO
  user_config
  (
    user_id,
    username,
    frequency,
    language,
    delivery,
    tags,
    notified_timestamp
  )
VALUES
  (
    %(user_id)s,
    %(username)s,
    %(frequency)s,
    %(language)s,
    %(delivery)s,
    %(tags)s,
    %(base_notified_timestamp_if_new_user)s
  )
ON DUPLICATE KEY UPDATE
  username = %(username)s,
  frequency = %(frequency)s,
  language = %(language)s,
  delivery = %(delivery)s,
  tags = %(tags)s