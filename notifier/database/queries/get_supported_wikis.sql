SELECT
  wiki_id AS id,
  wiki_uses_https AS secure
FROM
  context_wiki
WHERE
  context_wiki.wiki_service_configured = 1