CREATE TABLE IF NOT EXISTS user_config (
  user_id TEXT NOT NULL PRIMARY KEY,
  username TEXT NOT NULL,
  frequency TEXT NOT NULL,
  language TEXT NOT NULL,
  delivery TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS user_last_notified (
  user_id TEXT NOT NULL PRIMARY KEY,
  notified_timestamp INTEGER NOT NULL
);

CREATE TABLE manual_sub (
  user_id TEXT NOT NULL REFERENCES user_config (user_id),
  thread_id TEXT NOT NULL,
  post_id TEXT,
  sub INTEGER NOT NULL CHECK (sub IN (-1, 1)),
  UNIQUE (user_id, thread_id, post_id, sub)
);

CREATE TABLE IF NOT EXISTS global_override (
  wiki_id TEXT NOT NULL,
  override_settings_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS wiki (
  id TEXT NOT NULL PRIMARY KEY,
  name TEXT NOT NULL,
  secure INTEGER NOT NULL CHECK (secure IN (0, 1))
);

CREATE TABLE IF NOT EXISTS category (
  id TEXT NOT NULL PRIMARY KEY,
  name TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS thread (
  id TEXT NOT NULL PRIMARY KEY,
  title TEXT NOT NULL,
  wiki_id TEXT NOT NULL,
  category_id TEXT,
  creator_username TEXT,
  created_timestamp INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS post (
  id TEXT NOT NULL PRIMARY KEY,
  thread_id TEXT NOT NULL REFERENCES thread (id),
  parent_post_id TEXT REFERENCES post (id),
  posted_timestamp INTEGER NOT NULL,
  title TEXT NOT NULL,
  snippet TEXT NOT NULL,
  user_id TEXT NOT NULL,
  username TEXT NOT NULL
);