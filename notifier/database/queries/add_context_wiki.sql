INSERT INTO
  context_wiki
  (wiki_id, wiki_name, wiki_service_configured, wiki_uses_https)
VALUES
  (%(wiki_id)s, %(wiki_name)s, %(wiki_service_configured)s, %(wiki_uses_https)s)
ON DUPLICATE KEY UPDATE
  wiki_name = %(wiki_name)s,
  wiki_service_configured = %(wiki_service_configured)s,
  wiki_uses_https = %(wiki_uses_https)s
