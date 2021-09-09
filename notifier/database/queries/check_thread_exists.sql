SELECT EXISTS (
  SELECT
    1
  FROM
    thread
  WHERE
    id = %(id)s
)
