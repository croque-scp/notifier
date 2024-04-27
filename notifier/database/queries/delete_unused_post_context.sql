-- Purge context that is no longer relevant to any post

DELETE FROM context_forum_category
WHERE NOT EXISTS (
  SELECT NULL FROM notifiable_post WHERE
    notifiable_post.context_forum_category_id = context_forum_category.category_id
);

DELETE FROM context_thread
WHERE NOT EXISTS (
  SELECT NULL FROM notifiable_post WHERE
    notifiable_post.context_thread_id = context_thread.thread_id
);

DELETE FROM context_parent_post
WHERE NOT EXISTS (
  SELECT NULL FROM notifiable_post WHERE
    notifiable_post.context_parent_post_id = context_parent_post.post_id
);