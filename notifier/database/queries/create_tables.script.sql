--
-- Foreign key constraints are rarely used in this schema - while the
-- values of some columns do map to the values of others, it is not
-- important for all values to be represented in the corresponding table.
-- It would not make sense not to record posts made by a user just because
-- that user does not have a notification config, for example.
--
-- VARCHAR limits where appropriate have been selected to match the maximum
-- length of the corresponding value permitted by Wikidot.
--

CREATE TABLE IF NOT EXISTS user_config (
  user_id VARCHAR(20) NOT NULL PRIMARY KEY,
  username VARCHAR(20) NOT NULL,
  frequency VARCHAR(10) NOT NULL,
  language VARCHAR(5) NOT NULL,
  delivery VARCHAR(5) NOT NULL
);

CREATE TABLE IF NOT EXISTS user_last_notified (
  user_id VARCHAR(20) NOT NULL PRIMARY KEY,
  notified_timestamp INT UNSIGNED NOT NULL
);

CREATE TABLE manual_sub (
  user_id VARCHAR(20) NOT NULL REFERENCES user_config (user_id),
  thread_id VARCHAR(20) NOT NULL,
  post_id VARCHAR(20),
  sub TINYINT NOT NULL CHECK (sub IN (-1, 1)),
  UNIQUE (user_id, thread_id, post_id, sub)
);

CREATE TABLE IF NOT EXISTS global_override (
  wiki_id VARCHAR(50) NOT NULL,
  override_settings_json VARCHAR(2000) NOT NULL
);

CREATE TABLE IF NOT EXISTS wiki (
  id VARCHAR(50) NOT NULL PRIMARY KEY,
  name VARCHAR(200) NOT NULL,
  secure TINYINT(1) NOT NULL CHECK (secure IN (0, 1))
);

CREATE TABLE IF NOT EXISTS category (
  id VARCHAR(20) NOT NULL PRIMARY KEY,
  name VARCHAR(200) NOT NULL
);

CREATE TABLE IF NOT EXISTS thread (
  id VARCHAR(20) NOT NULL PRIMARY KEY,
  title VARCHAR(200) NOT NULL,
  wiki_id VARCHAR(50) NOT NULL,
  category_id VARCHAR(200),
  creator_username VARCHAR(20),
  created_timestamp INT UNSIGNED NOT NULL,
  is_deleted TINYINT(1) NOT NULL CHECK (is_deleted IN (0, 1)) DEFAULT 0
);

CREATE TABLE IF NOT EXISTS post (
  id VARCHAR(20) NOT NULL PRIMARY KEY,
  thread_id VARCHAR(20) NOT NULL REFERENCES thread (id),
  parent_post_id VARCHAR(20) REFERENCES post (id),
  posted_timestamp INT UNSIGNED NOT NULL,
  title VARCHAR(200) NOT NULL,
  snippet VARCHAR(200) NOT NULL,
  user_id VARCHAR(20) NOT NULL,
  username VARCHAR(20) NOT NULL,
  is_deleted TINYINT(1) NOT NULL CHECK (is_deleted IN (0, 1)) DEFAULT 0
);