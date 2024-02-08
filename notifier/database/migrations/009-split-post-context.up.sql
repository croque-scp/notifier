-- DELETE FROM thread WHERE is_deleted = 1;
-- DELETE FROM post WHERE is_deleted = 1;

START TRANSACTION;

-- Temporary for testing

DROP TABLE IF EXISTS notifiable_post;
DROP TABLE IF EXISTS context_wiki;
DROP TABLE IF EXISTS context_forum_category;
DROP TABLE IF EXISTS context_thread;
DROP TABLE IF EXISTS context_parent_post;
SELECT "post", COUNT(*) FROM post;

-- Set up new tables for split post data structure

CREATE TABLE notifiable_post (
  post_id          VARCHAR(20)  NOT NULL,
  posted_timestamp INT UNSIGNED NOT NULL,

  post_title   VARCHAR(200) NOT NULL,
  post_snippet VARCHAR(200) NOT NULL,

  author_user_id  VARCHAR(20) NOT NULL,
  author_username VARCHAR(20) NOT NULL,

  context_wiki_id           VARCHAR(20) NOT NULL,
  context_forum_category_id VARCHAR(20),
  context_thread_id         VARCHAR(20) NOT NULL,
  context_parent_post_id    VARCHAR(20),

  UNIQUE (post_id)
);

CREATE TABLE context_wiki (
  wiki_id                 VARCHAR(20)  NOT NULL,
  wiki_name               VARCHAR(200) NOT NULL,
  wiki_service_configured TINYINT(1)   NOT NULL,
  wiki_uses_https         TINYINT(1)   NOT NULL,

  UNIQUE (wiki_id)
);

CREATE TABLE context_forum_category (
  category_id   VARCHAR(20)  NOT NULL,
  category_name VARCHAR(200) NOT NULL,

  UNIQUE (category_id)
);

CREATE TABLE context_thread (
  thread_id                VARCHAR(20)  NOT NULL,
  thread_created_timestamp INT UNSIGNED NOT NULL,

  thread_title            VARCHAR(200) NOT NULL,
  thread_snippet          VARCHAR(200) NOT NULL,
  thread_creator_username VARCHAR(20),

  first_post_id                VARCHAR(20)  NOT NULL,
  first_post_author_user_id    VARCHAR(20)  NOT NULL,
  first_post_author_username   VARCHAR(20)  NOT NULL,
  first_post_created_timestamp INT UNSIGNED NOT NULL,

  UNIQUE (thread_id)
);

CREATE TABLE context_parent_post (
  post_id          VARCHAR(20)  NOT NULL,
  posted_timestamp INT UNSIGNED NOT NULL,

  post_title   VARCHAR(200) NOT NULL,
  post_snippet VARCHAR(200) NOT NULL,

  author_user_id  VARCHAR(20)  NOT NULL,
  author_username VARCHAR(20)  NOT NULL,

  UNIQUE (post_id)
);

-- Move existing posts into new tables

-- 1. Notifiable posts
-- Insert posts into this table if a user is going to be notified about them

INSERT INTO notifiable_post
SELECT
  post.id AS post_id,
  post.posted_timestamp AS posted_timestamp,
  post.title AS post_title,
  post.snippet AS post_snippet,
  post.user_id AS author_user_id,
  post.username AS author_username,
  wiki.id AS context_wiki_id,
  category.id AS context_forum_category_id,
  thread.id AS context_thread_id,
  parent_post.id AS context_parent_post_id
FROM
  post
  LEFT JOIN
  thread ON thread.id = post.thread_id
  LEFT JOIN
  thread_first_post AS lookup_thread_first_post ON lookup_thread_first_post.thread_id = thread.id
  LEFT JOIN
  post AS first_post_in_thread ON first_post_in_thread.id = lookup_thread_first_post.post_id
  LEFT JOIN
  wiki ON wiki.id = thread.wiki_id
  LEFT JOIN
  category ON category.id = thread.category_id
  LEFT JOIN
  post AS parent_post ON parent_post.id = post.parent_post_id;
SELECT "notifiable_post", COUNT(*) FROM notifiable_post;

-- 2. Context tables

-- 2.1. Wikis

INSERT INTO context_wiki
SELECT
  wiki.id AS wiki_id,
  wiki.name AS wiki_name,
  1 AS wiki_service_configured,
  wiki.secure AS wiki_uses_https
FROM
  wiki
WHERE
  EXISTS (
    SELECT NULL FROM
      notifiable_post
    WHERE
      notifiable_post.context_wiki_id = wiki.id
  );
SELECT "context_wiki", COUNT(*) FROM context_wiki;

-- 2.2. Categories

INSERT INTO context_forum_category
SELECT
  category.id AS category_id,
  category.name AS category_name
FROM
  category
WHERE
  EXISTS (
    SELECT NULL FROM
      notifiable_post
    WHERE
      notifiable_post.context_forum_category_id = category.id
  );
SELECT "context_forum_category", COUNT(*) FROM context_forum_category;

-- 2.3. Threads

INSERT INTO context_thread
SELECT
  thread.id AS thread_id,
  thread.created_timestamp AS thread_created_timestamp,
  thread.title AS thread_title,
  first_post_in_thread.snippet AS thread_snippet,
  thread.creator_username AS thread_creator_username,
  first_post_in_thread.id AS first_post_id,
  first_post_in_thread.user_id AS first_post_author_user_id,
  first_post_in_thread.username AS first_post_author_username,
  first_post_in_thread.posted_timestamp AS first_post_created_timestamp
FROM
  thread
  INNER JOIN
  thread_first_post AS lookup_thread_first_post ON lookup_thread_first_post.thread_id = thread.id
  INNER JOIN
  post AS first_post_in_thread ON first_post_in_thread.id = lookup_thread_first_post.post_id
WHERE
  EXISTS (
    SELECT NULL FROM
      notifiable_post
    WHERE
      notifiable_post.context_thread_id = thread.id
  );
SELECT "context_thread", COUNT(*) FROM context_thread;

-- 2.4. Parent posts

INSERT INTO context_parent_post
SELECT
  post.id AS post_id,
  post.posted_timestamp AS posted_timestamp,
  post.title AS post_title,
  post.snippet AS post_snippet,
  post.user_id AS author_user_id,
  post.username AS author_username
FROM
  post
WHERE
  EXISTS (
    SELECT NULL FROM
      notifiable_post
    WHERE
      notifiable_post.context_parent_post_id = post.id
  );
SELECT "context_parent_post", COUNT(*) FROM context_parent_post;

-- Drop old tables
DROP TABLE post;
DROP TABLE thread_first_post;
DROP TABLE thread;
DROP TABLE category;
DROP TABLE wiki;

COMMIT;