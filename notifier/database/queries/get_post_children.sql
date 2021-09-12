SELECT
  id
FROM
  post
WHERE
  parent_post_id = %(id)s
