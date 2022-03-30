CREATE TABLE IF NOT EXISTS log_dump (
  channel                 VARCHAR(10)  NOT NULL, -- like user_config.frequency
  start_timestamp         INT UNSIGNED NOT NULL,
  end_timestamp           INT UNSIGNED NOT NULL,
  sites_count             INT          NOT NULL,
  user_count              INT          NOT NULL,
  activated_user_count    INT          NOT NULL,
  notified_user_count     INT          NOT NULL,
  notified_post_count     INT          NOT NULL,
  notified_thread_count   INT          NOT NULL,
  downloaded_post_count   INT          NOT NULL,
  downloaded_thread_count INT          NOT NULL
);