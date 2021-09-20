CREATE TABLE meta (
  PRIMARY KEY (`key`),
  `key`   VARCHAR(20) NOT NULL,
  `value` VARCHAR(20) NOT NULL
);

INSERT INTO meta VALUES ('migration_version', '000');