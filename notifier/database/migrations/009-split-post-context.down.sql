START TRANSACTION;

-- Recover wikis

CREATE TABLE wiki (
  PRIMARY KEY (id),
  id     VARCHAR(50)  NOT NULL,
  name   VARCHAR(200) NOT NULL,
  secure TINYINT(1)   NOT NULL
);

INSERT INTO wiki
SELECT
  context_wiki.wiki_id AS id,
  context_wiki.wiki_name AS name,
  context_wiki.wiki_uses_https AS secure
FROM context_wiki;

DROP TABLE context_wiki;

-- Recover categories

CREATE TABLE category (
  PRIMARY KEY (id),
  id   VARCHAR(20)  NOT NULL,
  name VARCHAR(200) NOT NULL
);

INSERT INTO category
SELECT
  context_forum_category.category_id AS id,
  context_forum_category.category_name AS name
FROM context_forum_category;

DROP TABLE context_forum_category;

-- Recover threads

CREATE TABLE thread (
  PRIMARY KEY (id),
  id                VARCHAR(20)  NOT NULL,
  title             VARCHAR(200) NOT NULL,
  wiki_id           VARCHAR(50)  NOT NULL,
  category_id       VARCHAR(200),
  creator_username  VARCHAR(20),
  created_timestamp INT UNSIGNED NOT NULL,
  is_deleted        TINYINT(1)   NOT NULL DEFAULT 0
);

INSERT INTO thread
SELECT
  context_thread.thread_id AS id,
  context_thread.thread_title AS title,
  notifiable_post.context_wiki_id AS wiki_id,
  notifiable_post.context_forum_category_id AS category_id,
  context_thread.thread_creator_username AS creator_username,
  context_thread.first_post_created_timestamp AS created_timestamp,
  0 AS is_deleted
FROM
  context_thread
  INNER JOIN
  notifiable_post ON notifiable_post.post_id = (
    SELECT post_id FROM notifiable_post
    WHERE notifiable_post.context_thread_id = context_thread.thread_id
    LIMIT 1
  );

CREATE TABLE thread_first_post (
  PRIMARY KEY (thread_id),
  thread_id VARCHAR(20) NOT NULL,
  post_id   VARCHAR(20) NOT NULL
);

INSERT INTO thread_first_post
SELECT
  context_thread.thread_id AS thread_id,
  context_thread.first_post_id AS post_id
FROM context_thread;

-- Recover the remaing stored posts and salvage implied posts from thread and parent post contexts

CREATE TABLE post (
  PRIMARY KEY (id),
  id               VARCHAR(20)  NOT NULL,
  thread_id        VARCHAR(20)  NOT NULL,
  parent_post_id   VARCHAR(20),
  posted_timestamp INT UNSIGNED NOT NULL,
  title            VARCHAR(200) NOT NULL,
  snippet          VARCHAR(200) NOT NULL,
  user_id          VARCHAR(20)  NOT NULL,
  username         VARCHAR(20)  NOT NULL,
  is_deleted       TINYINT(1)   NOT NULL DEFAULT 0,
  FOREIGN KEY (thread_id)      REFERENCES thread (id),
  FOREIGN KEY (parent_post_id) REFERENCES post (id),
  INDEX post_author_id_index (user_id)
);

INSERT INTO post
SELECT
  context_parent_post.post_id AS id,
  notifiable_post.context_thread_id AS thread_id,
  NULL AS parent_post_id,
  context_parent_post.posted_timestamp AS posted_timestamp,
  context_parent_post.post_title AS title,
  context_parent_post.post_snippet AS snippet,
  context_parent_post.author_user_id AS user_id,
  context_parent_post.author_username AS username,
  0 AS is_deleted
FROM
  context_parent_post
  INNER JOIN
  notifiable_post ON notifiable_post.post_id = (
    SELECT post_id FROM notifiable_post
    WHERE notifiable_post.context_parent_post_id = context_parent_post.post_id
    LIMIT 1
  );
DROP TABLE context_parent_post;

INSERT INTO post
SELECT
  notifiable_post.post_id AS id,
  notifiable_post.context_thread_id AS thread_id,
  notifiable_post.context_parent_post_id AS parent_post_id,
  notifiable_post.posted_timestamp AS posted_timestamp,
  notifiable_post.post_title AS title,
  notifiable_post.post_snippet AS snippet,
  notifiable_post.author_user_id AS user_id,
  notifiable_post.author_username AS username,
  0 AS is_deleted
FROM notifiable_post
ON DUPLICATE KEY UPDATE id=id;

INSERT INTO post
SELECT
  context_thread.first_post_id AS id,
  context_thread.thread_id AS thread_id,
  NULL AS parent_post_id,
  context_thread.first_post_created_timestamp AS posted_timestamp,
  context_thread.thread_title AS title,
  context_thread.thread_snippet AS snippet,
  context_thread.first_post_author_user_id AS user_id,
  context_thread.first_post_author_username AS username,
  0 AS is_deleted
FROM context_thread
ON DUPLICATE KEY UPDATE id=id;

DROP TABLE context_thread;
DROP TABLE notifiable_post;

COMMIT;