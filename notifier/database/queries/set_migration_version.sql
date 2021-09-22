INSERT INTO
  meta
  (`key`, `value`)
VALUES
  ('migration_version', %(version)s)
ON DUPLICATE KEY UPDATE
  `value` = %(version)s