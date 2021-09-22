CREATE TABLE IF NOT EXISTS thread_first_post (
  PRIMARY KEY (thread_id),
  thread_id VARCHAR(20) NOT NULL,
  post_id   VARCHAR(20) NOT NULL
);

INSERT INTO
  thread_first_post
SELECT
  thread.id AS thread_id, post.id AS post_id
FROM
  thread
  INNER JOIN
  post ON post.id = (
    SELECT first_post.id FROM
      post AS first_post
    GROUP BY
      first_post.thread_id
    HAVING
      MIN(first_post.posted_timestamp)
      AND first_post.thread_id = thread.id
    LIMIT 1
  );
