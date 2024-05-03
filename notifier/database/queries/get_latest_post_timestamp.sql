SELECT
  MAX(posted_timestamp) as posted_timestamp
FROM
  notifiable_post
WHERE
  notifiable_post.context_wiki_id = %(wiki_id)s