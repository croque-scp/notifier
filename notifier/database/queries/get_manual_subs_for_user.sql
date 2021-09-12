SELECT
  thread_id, post_id, sub
FROM
  manual_sub
WHERE
  user_id = %(user_id)s
