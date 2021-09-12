-- Prepare a list of drop statements to drop all tables in the database.
-- Used for scrubbing the test database.

SELECT
  concat('DROP TABLE IF EXISTS `', table_name, '`;') AS scrub
FROM
  information_schema.tables
WHERE
  table_schema = %(db_name)s