INSERT INTO
  thread
  (id, title, wiki_id, category_id, creator_username, created_timestamp)
VALUES
  (
    %(id)s,
    %(title)s,
    %(wiki_id)s,
    %(category_id)s,
    %(creator_username)s,
    %(created_timestamp)s
  )
ON DUPLICATE KEY UPDATE
  title = %(title)s,
  wiki_id = %(wiki_id)s,
  category_id = %(category_id)s,
  creator_username = %(creator_username)s,
  created_timestamp = %(created_timestamp)s
