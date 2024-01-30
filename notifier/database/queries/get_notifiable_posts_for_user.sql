SELECT
  post.post_id AS id,
  post.posted_timestamp AS posted_timestamp,
  post.post_title AS title,
  post.post_snippet AS snippet,
  post.author_username AS username,

  context_wiki.wiki_id AS wiki_id,
  context_wiki.wiki_name AS wiki_name,
  context_wiki.wiki_uses_https AS wiki_secure,

  context_forum_category.category_id AS category_id,
  context_forum_category.category_name AS category_name,

  context_thread.thread_id AS thread_id,
  context_thread.thread_created_timestamp AS thread_timestamp,
  context_thread.thread_title AS thread_title,
  context_thread.thread_creator_username AS thread_creator,

  context_parent_post.post_id AS parent_post_id,
  context_parent_post.posted_timestamp AS parent_posted_timestamp,
  context_parent_post.post_title AS parent_title,
  context_parent_post.author_username AS parent_username

FROM
  notifiable_post AS post

  LEFT JOIN context_wiki
  ON context_wiki.wiki_id = post.context_wiki_id

  LEFT JOIN context_forum_category
  ON context_forum_category.category_id = post.context_forum_category_id

  LEFT JOIN context_thread
  ON context_thread.thread_id = post.context_thread_id

  LEFT JOIN context_parent_post
  ON context_parent_post.post_id = post.context_parent_post_id

WHERE
  -- Remove posts made by the user
  post.author_user_id <> %(user_id)s

  -- Remove posts from before the user was last notified
  AND post.posted_timestamp >= %(lower_timestamp)s

  -- Remove posts from after the start of this run
  AND post.posted_timestamp <= %(upper_timestamp)s

  