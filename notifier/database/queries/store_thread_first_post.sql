INSERT INTO
  thread_first_post
  (thread_id, post_id)
VALUES
  (%(thread_id)s, %(post_id)s)
ON DUPLICATE KEY UPDATE
  post_id = %(post_id)s
