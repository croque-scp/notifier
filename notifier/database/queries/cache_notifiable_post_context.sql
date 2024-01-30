-- Pre-joins posts to context tables to avoid repeating that for each user queried
CREATE TEMPORARY TABLE IF NOT EXISTS post_with_context
WITH cte AS (
  SELECT
    notifiable_post.author_user_id AS post_user_id,
    notifiable_post.posted_timestamp AS post_posted_timestamp,
    context_parent_post.post_id AS parent_post_id,
    context_parent_post.author_user_id AS parent_post_user_id,
    context_thread.thread_id AS thread_id,
    context_thread.first_post_author_user_id AS first_post_in_thread_user_id
  FROM
    notifiable_post
    LEFT JOIN
    context_wiki ON context_wiki.wiki_id = notifiable_post.context_wiki_id
    LEFT JOIN
    context_forum_category ON context_forum_category.category_id = notifiable_post.context_forum_category_id
    LEFT JOIN
    context_thread ON context_thread.thread_id = notifiable_post.context_thread_id
    LEFT JOIN
    context_parent_post ON context_parent_post.post_id = notifiable_post.context_parent_post_id
)
SELECT * FROM cte