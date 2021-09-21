SELECT
  id AS thread_id, NULL AS post_id, 1 AS sub
FROM
  thread
  LEFT JOIN
  post AS first_post ON thread.first_post_id = post.id
WHERE
  first_post.user_id = %(user_id)s
