SELECT
  thread_id, NULL AS post_id, 1 AS sub
FROM
  post
WHERE
  -- Get posts made by the user which are the first in the thread
  EXISTS (
    SELECT NULL FROM
      post AS first_post
    GROUP BY
      first_post.thread_id,
      first_post.user_id
    HAVING
      MIN(first_post.posted_timestamp)
      AND first_post.user_id = %(user_id)s
      AND first_post.thread_id = post.thread_id
  )
