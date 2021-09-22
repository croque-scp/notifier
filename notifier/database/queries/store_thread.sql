INSERT INTO
  thread
  (
    id,
    title,
    wiki_id,
    category_id,
    creator_username,
    created_timestamp,
    first_post_id
  )
VALUES
  (
    %(id)s,
    %(title)s,
    %(wiki_id)s,
    %(category_id)s,
    %(creator_username)s,
    %(created_timestamp)s,
    %(first_post_id)s
  )
ON DUPLICATE KEY UPDATE
  title = %(title)s,
  wiki_id = %(wiki_id)s,
  category_id = %(category_id)s,
  creator_username = %(creator_username)s,
  created_timestamp = %(created_timestamp)s,
  first_post_id = %(first_post_id)s
