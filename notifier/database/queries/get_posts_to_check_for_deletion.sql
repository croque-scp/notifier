SELECT
  context_wiki_id AS wiki_id,
  context_thread_id AS thread_id,
  post_id AS post_id
FROM
  notifiable_post
WHERE
  posted_timestamp BETWEEN (%(now)s - 3 * 3600) AND %(now)s
  OR posted_timestamp BETWEEN (%(now)s - 6 * 3600) AND (%(now)s - 5 * 3600)
  OR posted_timestamp BETWEEN (%(now)s - 12 * 3600) AND (%(now)s - 11 * 3600)
  OR posted_timestamp BETWEEN (%(now)s - 24 * 3600) AND (%(now)s - 23 * 3600)

  OR posted_timestamp BETWEEN (%(now)s - 1 * 86400 - 3600) AND (%(now)s - 1 * 86400)
  OR posted_timestamp BETWEEN (%(now)s - 3 * 86400 - 3600) AND (%(now)s - 3 * 86400)

  OR posted_timestamp BETWEEN (%(now)s - 7 * 86400 - 3600) AND (%(now)s - 7 * 86400)
  OR posted_timestamp BETWEEN (%(now)s - 14 * 86400 - 3600) AND (%(now)s - 14 * 86400)
  OR posted_timestamp BETWEEN (%(now)s - 28 * 86400 - 3600) AND (%(now)s - 28 * 86400)
  OR posted_timestamp BETWEEN (%(now)s - 56 * 86400 - 3600) AND (%(now)s - 56 * 86400)
  OR posted_timestamp BETWEEN (%(now)s - 112 * 86400 - 3600) AND (%(now)s - 112 * 86400)
  OR posted_timestamp BETWEEN (%(now)s - 224 * 86400 - 3600) AND (%(now)s - 224 * 86400)