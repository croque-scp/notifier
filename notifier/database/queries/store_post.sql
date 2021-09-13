INSERT INTO
  post
  (
    id,
    thread_id,
    parent_post_id,
    posted_timestamp,
    title,
    snippet,
    user_id,
    username
  )
VALUES
  (
    %(id)s,
    %(thread_id)s,
    %(parent_post_id)s,
    %(posted_timestamp)s,
    %(title)s,
    %(snippet)s,
    %(user_id)s,
    %(username)s
  )
ON DUPLICATE KEY UPDATE
  thread_id = %(thread_id)s,
  parent_post_id = %(parent_post_id)s,
  posted_timestamp = %(posted_timestamp)s,
  title = %(title)s,
  snippet = %(snippet)s,
  user_id = %(user_id)s,
  username = %(username)s
