ALTER TABLE
  thread
ADD COLUMN
  first_post_id VARCHAR(20)
AFTER
  created_timestamp;

UPDATE
  thread
SET
  first_post_id = (
    SELECT first_post.id FROM
      post AS first_post
    GROUP BY
      first_post.thread_id
    HAVING
      MIN(first_post.posted_timestamp)
      AND first_post.thread_id = thread.id
    LIMIT 1
  );

UPDATE meta SET `value` = '001' WHERE `key` = 'migration_version';