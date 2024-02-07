SELECT
  user_config.user_id AS user_id
FROM
  user_config
WHERE
  -- Only users on the given channel
  user_config.frequency = %(frequency)s

  -- Only users with a notification waiting for them
  AND EXISTS (
    SELECT NULL FROM
      post_with_context

      LEFT JOIN manual_sub AS thread_sub
      ON thread_sub.user_id = user_config.user_id
      AND thread_sub.thread_id = post_with_context.thread_id
      AND thread_sub.post_id IS NULL

      LEFT JOIN manual_sub AS post_sub
      ON post_sub.user_id = user_config.user_id
      AND post_sub.thread_id = post_with_context.thread_id
      AND post_sub.post_id = post_with_context.parent_post_id

    WHERE
      -- Remove posts made by the user
      post_with_context.post_user_id <> user_config.user_id

      -- Only posts posted since the user was last notified
      AND post_with_context.post_posted_timestamp > user_config.notified_timestamp

      -- Only posts matching thread or post subscription criteria
      AND (
        -- Posts in threads started by the user
        post_with_context.first_post_in_thread_user_id = user_config.user_id

        -- Replies to posts made by the user
        OR post_with_context.parent_post_user_id = user_config.user_id

        -- Manual subscriptions
        OR thread_sub.sub = 1
        OR post_sub.sub = 1
      )

      -- Manual unsubscriptions
      AND (
        thread_sub.sub IS NULL OR thread_sub.sub = 1
        -- Post reply overrides thread unsubscription
        OR post_sub.sub = 1
        OR post_with_context.parent_post_user_id = user_config.user_id
      )
      AND (post_sub.sub IS NULL OR post_sub.sub = 1)
  )