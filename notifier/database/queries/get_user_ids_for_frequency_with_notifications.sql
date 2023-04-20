SELECT
  user_config.user_id AS user_id
FROM
  user_config
  LEFT JOIN
  user_last_notified ON user_config.user_id = user_last_notified.user_id
WHERE
  -- Only users on the given channel
  user_config.frequency = %(frequency)s

  -- Only users with a notification waiting for them
  AND EXISTS (
    SELECT NULL FROM
      post
      INNER JOIN
      thread ON thread.id = post.thread_id
      LEFT JOIN
      post AS parent_post ON parent_post.id = post.parent_post_id
      INNER JOIN
      thread_first_post ON thread_first_post.thread_id = thread.id
      INNER JOIN
      post AS first_post_in_thread ON first_post_in_thread.id = thread_first_post.post_id
    WHERE
      -- Remove deleted posts
      post.is_deleted = 0

      -- Remove posts made by the user
      AND post.user_id <> user_config.user_id

      -- Only posts posted since the user was last notified
      AND post.posted_timestamp > user_last_notified.notified_timestamp

      -- Remove deleted threads
      AND thread.is_deleted = 0

      -- Only posts matching thread or post subscription criteria
      AND (
        -- Posts in threads started by the user
        first_post_in_thread.user_id = user_config.user_id

        -- Replies to posts made by the user
        OR parent_post.user_id = user_config.user_id

        -- Posts in threads subscribed to and replies to posts subscribed to
        OR EXISTS (
          SELECT NULL FROM
            manual_sub
          WHERE
            manual_sub.user_id = user_config.user_id
            AND manual_sub.thread_id = thread.id
            AND (
              manual_sub.post_id IS NULL  -- Threads
              OR manual_sub.post_id = parent_post.id  -- Post replies
            )
            AND manual_sub.sub = 1
        )
      )

      -- Remove posts/replies in/to threads/posts unsubscribed from
      AND NOT EXISTS (
        SELECT NULL FROM
          manual_sub
        WHERE
          manual_sub.user_id = user_config.user_id
          AND manual_sub.thread_id = thread.id
          AND (
            manual_sub.post_id IS NULL  -- Threads
            OR manual_sub.post_id = parent_post.id  -- Post replies
          )
          AND manual_sub.sub = -1
      )
  )