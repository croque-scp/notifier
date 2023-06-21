CREATE TEMPORARY TABLE IF NOT EXISTS post_with_context
WITH cte AS (
  SELECT
    post.user_id AS post_user_id,
    post.posted_timestamp AS post_posted_timestamp,
    parent_post.id AS parent_post_id,
    parent_post.user_id AS parent_post_user_id,
    thread.id AS thread_id,
    first_post_in_thread.user_id AS first_post_in_thread_user_id
  FROM
    post
    INNER JOIN
    thread ON thread.id = post.thread_id
    INNER JOIN
    thread_first_post ON thread_first_post.thread_id = thread.id
    INNER JOIN
    post AS first_post_in_thread ON first_post_in_thread.id = thread_first_post.post_id
    LEFT JOIN
    post AS parent_post ON parent_post.id = post.parent_post_id
  WHERE
    -- Remove deleted threads/posts
    thread.is_deleted = 0 AND post.is_deleted = 0
)
SELECT * FROM cte