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
  INNER JOIN
  thread ON thread.id = post.thread_id
  INNER JOIN
  wiki ON wiki.id = thread.wiki_id
  INNER JOIN
  thread_first_post ON thread_first_post.thread_id = thread.id
  INNER JOIN
  post AS first_post_in_thread ON first_post_in_thread.id = thread_first_post.post_id
  LEFT JOIN
  category ON category.id = thread.category_id
  LEFT JOIN
  manual_sub AS thread_sub ON (
    thread_sub.user_id = %(user_id)s
    AND thread_sub.thread_id = thread.id
    AND thread_sub.post_id IS NULL
  )
  LEFT JOIN
  post AS user_response_child_post ON (
    user_response_child_post.parent_post_id = post.id
    AND user_response_child_post.user_id = %(user_id)s
  )
WHERE
  -- Remove deleted posts
  post.is_deleted = 0

  -- Remove posts made by the user
  AND post.user_id <> %(user_id)s

  -- Remove posts not posted in the current frequency channel
  AND post.posted_timestamp BETWEEN %(lower_timestamp)s AND %(upper_timestamp)s

  -- Remove posts in deleted threads
  AND thread.is_deleted = 0

  AND (
    -- Get posts in threads subscribed to
    thread_sub.sub = 1

    -- Get posts in threads started by the user
    OR first_post_in_thread.user_id = %(user_id)s
  )

  -- Remove posts in threads unsubscribed from
  AND (thread_sub.sub <> -1 OR thread_sub.sub IS NULL)

  -- Remove posts the user already responded to
  AND user_response_child_post.id IS NULL
ORDER BY
  wiki.id,
  category.id,
  thread.id,
  post.posted_timestamp
