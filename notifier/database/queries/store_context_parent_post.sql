INSERT INTO
  context_parent_post
  (
    post_id,
    posted_timestamp,
    post_title,
    post_snippet,
    author_user_id,
    author_username
  )
VALUES
  (
    %(post_id)s,
    %(posted_timestamp)s,
    %(post_title)s,
    %(post_snippet)s,
    %(author_user_id)s,
    %(author_username)s
  )
ON DUPLICATE KEY UPDATE
  posted_timestamp = %(posted_timestamp)s,
  post_title = %(post_title)s,
  post_snippet = %(post_snippet)s,
  author_user_id = %(author_user_id)s,
  author_username = %(author_username)s