UPDATE
  context_wiki
SET
  new_posts_checked_timestamp = %(timestamp)s
WHERE
  context_wiki.wiki_id = %(wiki_id)s