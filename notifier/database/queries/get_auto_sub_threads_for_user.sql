SELECT
  thread.id AS thread_id, NULL AS post_id, 1 AS sub
FROM
  thread
  LEFT JOIN
  thread_first_post ON thread_first_post.thread_id = thread.id
  LEFT JOIN
  post AS first_post ON thread_first_post.post_id = first_post.id
WHERE
  first_post.user_id = %(user_id)s
