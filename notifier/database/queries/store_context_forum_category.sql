INSERT INTO
  context_forum_category
  (category_id, category_name)
VALUES
  (%(category_id)s, %(category_name)s)
ON DUPLICATE KEY UPDATE
  category_name = %(category_name)s