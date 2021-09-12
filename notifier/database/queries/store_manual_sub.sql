INSERT IGNORE INTO
  manual_sub
  (user_id, thread_id, post_id, sub)
VALUES
  (%(user_id)s, %(thread_id)s, %(post_id)s, %(sub)s)
