INSERT INTO
  activation_log_dump
  (
    start_timestamp,
    config_start_timestamp,
    config_end_timestamp,
    getpost_start_timestamp,
    getpost_end_timestamp,
    notify_start_timestamp,
    notify_end_timestamp,
    end_timestamp,

    new_post_count,
    new_thread_count,
    checked_thread_count,

    site_count,
    user_count,
    post_count,
    thread_count
  )
  VALUES
  (
    %(start_timestamp)s,
    %(config_start_timestamp)s,
    %(config_end_timestamp)s,
    %(getpost_start_timestamp)s,
    %(getpost_end_timestamp)s,
    %(notify_start_timestamp)s,
    %(notify_end_timestamp)s,
    %(end_timestamp)s,

    %(new_post_count)s,
    %(new_thread_count)s,
    %(checked_thread_count)s,

    %(site_count)s,
    %(user_count)s,
    %(post_count)s,
    %(thread_count)s
  )
