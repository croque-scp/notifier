SELECT EXISTS (
  SELECT NULL FROM
    post
  WHERE
    id = %(id)s
) AS post_exists
