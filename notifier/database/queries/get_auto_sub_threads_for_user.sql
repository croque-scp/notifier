SELECT
  id AS thread_id, NULL AS post_id, 1 AS sub
FROM
  thread
WHERE
  -- Get posts made by the user which are the first in the thread
  %(user_id)s IN (
    SELECT first_post.user_id FROM
      post AS first_post
    GROUP BY
      first_post.thread_id
    HAVING
      MIN(first_post.posted_timestamp)
      AND first_post.thread_id = thread.id
  )
