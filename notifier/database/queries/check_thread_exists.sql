SELECT EXISTS (
  SELECT NUll FROM
    thread
  WHERE
    id = %(id)s
) AS thread_exists
