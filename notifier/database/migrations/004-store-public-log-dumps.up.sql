-- Start timestamps are marked unique to prompt MySQL into using them as the clustered index

CREATE TABLE IF NOT EXISTS channel_log_dump (
  channel                 VARCHAR(10)       NOT NULL, -- like user_config.frequency
  start_timestamp         INT UNSIGNED      NOT NULL UNIQUE,
  end_timestamp           INT UNSIGNED      NOT NULL,
  user_count              SMALLINT UNSIGNED NOT NULL,
  notified_user_count     SMALLINT UNSIGNED NOT NULL,
  notified_post_count     SMALLINT UNSIGNED NOT NULL,
  notified_thread_count   SMALLINT UNSIGNED NOT NULL
);

CREATE TABLE IF NOT EXISTS activation_log_dump (
  start_timestamp         INT UNSIGNED       NOT NULL UNIQUE,
  config_start_timestamp  INT UNSIGNED       NOT NULL,
  config_end_timestamp    INT UNSIGNED       NOT NULL,
  getpost_start_timestamp INT UNSIGNED       NOT NULL,
  getpost_end_timestamp   INT UNSIGNED       NOT NULL,
  notify_start_timestamp  INT UNSIGNED       NOT NULL,
  notify_end_timestamp    INT UNSIGNED       NOT NULL,
  end_timestamp           INT UNSIGNED       NOT NULL,

  new_post_count          SMALLINT UNSIGNED  NOT NULL,
  new_thread_count        SMALLINT UNSIGNED  NOT NULL,
  checked_thread_count    SMALLINT UNSIGNED  NOT NULL,

  site_count              SMALLINT UNSIGNED  NOT NULL,
  user_count              SMALLINT UNSIGNED  NOT NULL,
  post_count              MEDIUMINT UNSIGNED NOT NULL,
  thread_count            MEDIUMINT UNSIGNED NOT NULL
);
