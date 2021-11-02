ALTER TABLE
  user_config
ADD COLUMN
  tags VARCHAR(2000) NOT NULL;

UPDATE
  user_config
SET
  tags = "";