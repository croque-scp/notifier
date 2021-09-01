SELECT
  post.id AS id,
  post.title AS title,
  post.username AS username,
  post.posted_timestamp AS posted_timestamp,
  post.snippet AS snippet,
  thread.id AS thread_id,
  thread.title AS thread_title,
  thread.creator_username AS thread_creator,
  thread.created_timestamp AS thread_timestamp,
  wiki.id AS wiki_id,
  wiki.name AS wiki_name,
  wiki.secure AS wiki_secure,
  category.id AS category_id,
  category.name AS category_name
FROM
  post
  LEFT JOIN
  thread ON post.thread_id = thread.id
  LEFT JOIN
  wiki ON thread.wiki_id = wiki.id
  LEFT JOIN
  category ON thread.category_id = category.id
WHERE
  (
    -- Get posts in threads subscribed to
    EXISTS (
      SELECT NULL FROM
        manual_sub
      WHERE
        manual_sub.user_id = :user_id
        AND manual_sub.thread_id = thread.id
        AND manual_sub.post_id IS NULL
        AND manual_sub.sub = 1
    )

    -- Get posts in threads started by the user
    OR EXISTS (
      SELECT NULL FROM
        post AS first_post
      GROUP BY
        first_post.thread_id
      HAVING
        MIN(first_post.posted_timestamp)
        AND first_post.user_id = :user_id
        AND first_post.thread_id = post.thread_id
    )
  )

  -- Remove posts in deleted threads
  AND thread.is_deleted = 0

  -- Remove deleted posts
  AND post.is_deleted = 0

  -- Remove posts in threads unsubscribed from
  AND NOT EXISTS (
    SELECT NULL FROM
      manual_sub
    WHERE
      manual_sub.user_id = :user_id
      AND manual_sub.thread_id = thread.id
      AND manual_sub.post_id IS NULL
      AND manual_sub.sub = -1
  )

  -- Remove posts not posted in the current frequency channel
  AND post.posted_timestamp BETWEEN :lower_timestamp AND :upper_timestamp

  -- Remove posts made by the user
  AND post.user_id <> :user_id

  -- Remove posts the user already responded to
  AND NOT EXISTS (
    SELECT NULL FROM
      post AS child_post
    WHERE
      child_post.parent_post_id = post.id
      AND child_post.user_id = :user_id
  )
ORDER BY
  wiki.id,
  category.id,
  thread.id,
  post.posted_timestamp