SELECT
  thread_id, id AS post_id, 1 AS sub
FROM
  post
WHERE
  post.user_id = :user_id