INSERT INTO
  notifiable_post
  (
    post_id,
    posted_timestamp,
    post_title,
    post_snippet,
    author_user_id,
    author_username,
    context_wiki_id,
    context_forum_category_id,
    context_thread_id,
    context_parent_post_id
  )
VALUES
  (
    %(post_id)s,
    %(posted_timestamp)s,
    %(post_title)s,
    %(post_snippet)s,
    %(author_user_id)s,
    %(author_username)s,
    %(context_wiki_id)s,
    %(context_forum_category_id)s,
    %(context_thread_id)s,
    %(context_parent_post_id)s
  )
ON DUPLICATE KEY UPDATE
  posted_timestamp = %(posted_timestamp)s,
  post_title = %(post_title)s,
  post_snippet = %(post_snippet)s,
  author_user_id = %(author_user_id)s,
  author_username = %(author_username)s,
  context_wiki_id = %(context_wiki_id)s,
  context_forum_category_id = %(context_forum_category_id)s,
  context_thread_id = %(context_thread_id)s,
  context_parent_post_id = %(context_parent_post_id)s