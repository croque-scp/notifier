SELECT
  new_posts_checked_timestamp AS posted_timestamp
FROM
  context_wiki
WHERE
  context_wiki.wiki_id = %(wiki_id)s