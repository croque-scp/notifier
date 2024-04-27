DELETE FROM
  notifiable_post
WHERE
  notifiable_post.context_thread_id = %(thread_id)s