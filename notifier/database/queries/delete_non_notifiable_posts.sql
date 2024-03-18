START TRANSACTION;

-- Purge posts that are no longer considered notifiable

DELETE
  notifiable_post
FROM
  notifiable_post

  INNER JOIN context_thread
  ON context_thread.thread_id = notifiable_post.context_thread_id

  LEFT JOIN context_parent_post
  ON context_parent_post.post_id = notifiable_post.context_parent_post_id
WHERE
  -- Remove posts older than 1 year, no matter what
  notifiable_post.posted_timestamp < ((
    SELECT latest_timestamp FROM (
      SELECT
        MAX(posted_timestamp) AS latest_timestamp
      FROM notifiable_post
    ) AS t
  ) - (60 * 60 * 24 * 365))

  -- Remove posts for which there exist 0 users who will be notified about it
  OR NOT EXISTS (
    -- Attempt to find a user who will be notified by this post
    SELECT NULL FROM
      user_config

      LEFT JOIN manual_sub AS thread_sub
      ON thread_sub.user_id = user_config.user_id
      AND thread_sub.thread_id = notifiable_post.context_thread_id
      AND thread_sub.post_id IS NULL

      LEFT JOIN manual_sub AS post_sub
      ON post_sub.user_id = user_config.user_id
      AND post_sub.thread_id = notifiable_post.context_thread_id
      AND post_sub.post_id = notifiable_post.context_parent_post_id

    WHERE
      -- Include only users with chosen frequency in a defined list - other users e.g. those on the 'never' frequency are effectively unsubscribed
      user_config.frequency IN (
        "hourly", "8hourly", "daily", "weekly", "monthly"
      )

      -- Users are not notified about their own posts
      AND user_config.user_id <> notifiable_post.author_user_id

      -- Users whose last notified post was earlier than this one
      AND user_config.notified_timestamp <= notifiable_post.posted_timestamp

      -- Filter out users unsubscribed to this post
      AND (
        thread_sub.sub IS NULL OR thread_sub.sub = 1
        -- Post reply overrides thread unsubscription
        OR post_sub.sub = 1
        OR context_parent_post.author_user_id = user_config.user_id
      )
      AND (post_sub.sub IS NULL OR post_sub.sub = 1)

      -- Only users subscribed to this post
      AND (
        -- Posts in threads started by the user
        context_thread.first_post_author_user_id = user_config.user_id

        -- Replies to posts made by the user
        OR context_parent_post.author_user_id = user_config.user_id

        -- Manual subscriptions
        OR thread_sub.sub = 1
        OR post_sub.sub = 1
      )
  );

-- Purge context that is no longer relevant to any post

DELETE FROM context_forum_category
WHERE NOT EXISTS (
  SELECT NULL FROM notifiable_post WHERE
    notifiable_post.context_forum_category_id = context_forum_category.category_id
);

DELETE FROM context_thread
WHERE NOT EXISTS (
  SELECT NULL FROM notifiable_post WHERE
    notifiable_post.context_thread_id = context_thread.thread_id
);

DELETE FROM context_parent_post
WHERE NOT EXISTS (
  SELECT NULL FROM notifiable_post WHERE
    notifiable_post.context_parent_post_id = context_parent_post.post_id
);

COMMIT;