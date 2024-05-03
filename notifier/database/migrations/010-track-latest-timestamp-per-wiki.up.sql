ALTER TABLE
  context_wiki
ADD COLUMN
  new_posts_checked_timestamp INT UNSIGNED NOT NULL;

UPDATE
  context_wiki
SET
  new_posts_checked_timestamp = 0;
