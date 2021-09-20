--
-- This is the canonical form of the database schema, accurate after all
-- migrations up to and including the one stated below have been applied.
--
-- Foreign key constraints are rarely used in this schema - while the
-- values of some columns do map to the values of others, it is not
-- important for all values to be represented in the corresponding table.
-- It would not make sense not to record posts made by a user just because
-- that user does not have a notification config, for example.
--
-- VARCHAR limits where appropriate have been selected to match the maximum
-- length of the corresponding value permitted by Wikidot. Category,
-- thread, post and user IDs have been arbitrarily given a limit of 20
-- characters.
--

CREATE TABLE meta (
  PRIMARY KEY (`key`),
  `key`   VARCHAR(20) NOT NULL,
  `value` VARCHAR(20) NOT NULL
);
INSERT INTO meta VALUES ('migration_version', '000');

CREATE TABLE user_config (
  PRIMARY KEY (user_id),
  user_id   VARCHAR(20) NOT NULL,
  username  VARCHAR(20) NOT NULL,
  frequency VARCHAR(10) NOT NULL,
  language  VARCHAR(5)  NOT NULL,
  delivery  VARCHAR(5)  NOT NULL
);

CREATE TABLE user_last_notified (
  PRIMARY KEY (user_id),
  user_id            VARCHAR(20)  NOT NULL,
  notified_timestamp INT UNSIGNED NOT NULL
);

CREATE TABLE manual_sub (
  user_id   VARCHAR(20) NOT NULL,
  thread_id VARCHAR(20) NOT NULL,
  post_id   VARCHAR(20),
  sub       TINYINT     NOT NULL CHECK (sub IN (-1, 1)),
  FOREIGN KEY (user_id) REFERENCES user_config (user_id) ON DELETE CASCADE,
  UNIQUE (user_id, thread_id, post_id, sub)
);

CREATE TABLE global_override (
  wiki_id                VARCHAR(50)   NOT NULL,
  override_settings_json VARCHAR(2000) NOT NULL
);

CREATE TABLE wiki (
  PRIMARY KEY (id),
  id     VARCHAR(50)  NOT NULL,
  name   VARCHAR(200) NOT NULL,
  secure TINYINT(1)   NOT NULL
);

CREATE TABLE category (
  PRIMARY KEY (id),
  id   VARCHAR(20)  NOT NULL,
  name VARCHAR(200) NOT NULL
);

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
  FOREIGN KEY (parent_post_id) REFERENCES post (id)
);