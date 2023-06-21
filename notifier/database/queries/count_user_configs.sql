SELECT
  COUNT(*) AS count
FROM
  user_config
WHERE
  user_config.frequency <> "never"