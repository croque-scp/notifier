INSERT OR REPLACE INTO
  thread
  (id, title, wiki_id, category_id, creator_username, created_timestamp)
VALUES
  (:id, :title, :wiki_id, :category_id, :creator_username, :created_timestamp)