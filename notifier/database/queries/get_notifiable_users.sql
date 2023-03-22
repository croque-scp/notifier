SELECT
  user_config.user_id AS user_id,
  user_config.username AS username,
  user_config.frequency AS frequency,
  user_config.language AS language,
  user_config.delivery AS delivery,
  user_config.tags AS tags,
  user_last_notified.notified_timestamp AS last_notified_timestamp
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
      INNER JOIN
      post AS parent_post ON parent_post.id = post.parent_post_id
      INNER JOIN
      thread_first_post ON thread_first_post.thread_id = thread.id
      INNER JOIN
      post AS first_post_in_thread ON first_post_in_thread.id = thread_first_post.post_id
      LEFT JOIN
      manual_sub AS user_manual_sub_to_post ON (
        user_manual_sub_to_post.user_id = user_config.user_id
        AND user_manual_sub_to_post.thread_id = thread.id
        AND user_manual_sub_to_post.post_id = parent_post.id
      )
      LEFT JOIN
      manual_sub AS user_manual_sub_to_thread ON (
        thread_sub.user_id = user_config.user_id
        AND thread_sub.thread_id = thread.id
        AND thread_sub.post_id IS NULL
      )
    WHERE
      -- Remove deleted posts
      post.is_deleted = 0

      -- Remove posts made by the user
      AND post.user_id <> user_config.user_id

      -- Only posts posted since the user was last notified
      AND post.posted_timestamp >= user_last_notified.notified_timestamp

      -- Remove deleted threads
      AND thread.is_deleted = 0

      -- Only posts matching thread or post subscription criteria
      AND (
        -- Posts in threads subscribed to
        user_manual_sub_to_thread.sub = 1

        -- Posts in threads started by the user
        OR first_post_in_thread.user_id = user_config.user_id

        -- Replies to posts subscribed to
        OR user_manual_sub_to_post.sub = 1

        -- Replies to posts made by the user
        OR parent_post.user_id = user_config.user_id
      )

      -- Remove posts in threads unsubscribed from
      AND (user_manual_sub_to_thread.sub <> -1 OR user_manual_sub_to_thread.sub IS NULL)
  )