INSERT INTO
  context_thread
  (
    thread_id,
    thread_created_timestamp,
    thread_title,
    thread_snippet,
    thread_creator_username,
    first_post_id,
    first_post_author_user_id,
    first_post_author_username,
    first_post_created_timestamp
  )
VALUES
  (
    %(thread_id)s,
    %(thread_created_timestamp)s,
    %(thread_title)s,
    %(thread_snippet)s,
    %(thread_creator_username)s,
    %(first_post_id)s,
    %(first_post_author_user_id)s,
    %(first_post_author_username)s,
    %(first_post_created_timestamp)s
  )
ON DUPLICATE KEY UPDATE
  thread_created_timestamp = %(thread_created_timestamp)s,
  thread_title = %(thread_title)s,
  thread_snippet = %(thread_snippet)s,
  thread_creator_username = %(thread_creator_username)s,
  first_post_id = %(first_post_id)s,
  first_post_author_user_id = %(first_post_author_user_id)s,
  first_post_author_username = %(first_post_author_username)s,
  first_post_created_timestamp = %(first_post_created_timestamp)s