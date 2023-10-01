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
  post AS parent_post ON parent_post.id = post.parent_post_id
  LEFT JOIN
  category ON category.id = thread.category_id
  LEFT JOIN
  manual_sub AS post_sub ON (
    post_sub.user_id = %(user_id)s
    AND post_sub.thread_id = thread.id
    AND post_sub.post_id = parent_post.id
  )
WHERE
  -- Remove deleted posts
  post.is_deleted = 0

  -- Remove posts made by the user
  AND post.user_id <> %(user_id)s

  -- Remove posts not posted in the current frequency channel
  AND post.posted_timestamp BETWEEN %(lower_timestamp)s AND %(upper_timestamp)s

  -- Select only posts in non-deleted threads
  AND thread.is_deleted = 0

  AND (
    -- Get replies to posts subscribed to
    post_sub.sub = 1

    -- Get replies to posts made by the user
    OR parent_post.user_id = %(user_id)s
  )

  -- Remove replies to posts unsubscribed from
  -- Sub table is added to this query via left join, so the null check matches when the user has no manual subscription to or from a post
  AND (post_sub.sub <> -1 OR post_sub.sub IS NULL)
ORDER BY
  wiki.id,
  category.id,
  thread.id,
  parent_post.id,
  post.posted_timestamp
