WITH post_with_flags AS (
  SELECT
    post.post_id AS id,
    post.posted_timestamp AS posted_timestamp,
    post.post_title AS title,
    post.post_snippet AS snippet,
    post.author_username AS username,

    context_wiki.wiki_id AS wiki_id,
    context_wiki.wiki_name AS wiki_name,
    context_wiki.wiki_uses_https AS wiki_secure,

    context_forum_category.category_id AS category_id,
    context_forum_category.category_name AS category_name,

    context_thread.thread_id AS thread_id,
    context_thread.thread_created_timestamp AS thread_timestamp,
    context_thread.thread_title AS thread_title,
    context_thread.thread_creator_username AS thread_creator,

    context_parent_post.post_id AS parent_post_id,
    context_parent_post.posted_timestamp AS parent_posted_timestamp,
    context_parent_post.post_title AS parent_title,
    context_parent_post.author_username AS parent_username,

    -- Flags indicating the reasons that a post emits a notification

    CASE WHEN (
      thread_sub.sub = 1
    ) THEN 1 ELSE 0 END AS flag_user_subscribed_to_thread,

    CASE WHEN (
      post_sub.sub = 1
    ) THEN 1 ELSE 0 END AS flag_user_subscribed_to_post,

    CASE WHEN (
      context_thread.first_post_author_user_id = %(user_id)s
    ) THEN 1 ELSE 0 END AS flag_user_started_thread,

    CASE WHEN (
      context_parent_post.author_user_id = %(user_id)s
    ) THEN 1 ELSE 0 END AS flag_user_posted_parent

  FROM
    notifiable_post AS post

    INNER JOIN context_wiki
    ON context_wiki.wiki_id = post.context_wiki_id

    LEFT JOIN context_forum_category
    ON context_forum_category.category_id = post.context_forum_category_id

    INNER JOIN context_thread
    ON context_thread.thread_id = post.context_thread_id

    LEFT JOIN context_parent_post
    ON context_parent_post.post_id = post.context_parent_post_id

    LEFT JOIN manual_sub AS thread_sub
    ON thread_sub.user_id = %(user_id)s
    AND thread_sub.thread_id = context_thread.thread_id
    AND thread_sub.post_id IS NULL

    LEFT JOIN manual_sub AS post_sub
    ON post_sub.user_id = %(user_id)s
    AND post_sub.post_id = post.post_id
    AND post_sub.thread_id = context_thread.thread_id

  WHERE
    -- Remove posts made by the user
    post.author_user_id <> %(user_id)s

    -- Remove posts from before the user was last notified
    AND post.posted_timestamp >= %(lower_timestamp)s

    -- Remove posts from after the start of this run
    AND post.posted_timestamp <= %(upper_timestamp)s

    -- Remove posts unsubscribed from
    AND (thread_sub.sub IS NULL OR thread_sub.sub = 1)
    AND (post_sub.sub IS NULL OR post_sub.sub = 1)
)

SELECT * FROM post_with_flags

-- From the CTE select only posts with at least one flag active
WHERE
  flag_user_subscribed_to_thread
  OR flag_user_subscribed_to_post
  OR flag_user_started_thread
  OR flag_user_posted_parent

ORDER BY
  wiki_id, category_id, thread_id, parent_post_id, posted_timestamp