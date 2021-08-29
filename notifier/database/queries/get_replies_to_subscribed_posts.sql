SELECT
  post.id AS id,
  post.title AS title,
  post.username AS username,
  post.posted_timestamp AS posted_timestamp,
  post.snippet AS snippet,
  parent_post.id AS parent_post_id,
  parent_post.title AS parent_title,
  parent_post.username AS parent_username,
  parent_post.posted_timestamp AS parent_posted_timestamp,
  thread.id AS thread_id,
  thread.title AS thread_title,
  thread.creator_username AS thread_creator,
  thread.created_timestamp AS thread_timestamp,
  wiki.id AS wiki_id,
  wiki.name as wiki_name,
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
  post AS parent_post ON post.parent_post_id = parent_post.id
  LEFT JOIN
  category ON thread.category_id = category.id
WHERE
  (
    -- Get replies to posts subscribed to
    EXISTS (
      SELECT NULL FROM
        manual_sub
      WHERE
        manual_sub.post_id = parent_post.id
        AND manual_sub.thread_id = thread.id
        AND manual_sub.user_id = :user_id
        AND manual_sub.sub = 1
    )

    -- Get replies to posts made by the user
    OR parent_post.user_id = :user_id
  )

  -- Select only posts in non-deleted threads
  AND thread.is_deleted = 0

  -- Remove replies to posts unsubscribed from
  AND NOT EXISTS (
    SELECT NULL FROM
      manual_sub
    WHERE
      manual_sub.post_id = parent_post.id
      AND manual_sub.thread_id = thread.id
      AND manual_sub.user_id = :user_id
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
  parent_post.id,
  post.posted_timestamp