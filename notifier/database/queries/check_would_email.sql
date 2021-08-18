SELECT EXISTS (
  SELECT
    1
  FROM
    user_config
  WHERE
    frequency = :frequency
    AND delivery = "email"
)