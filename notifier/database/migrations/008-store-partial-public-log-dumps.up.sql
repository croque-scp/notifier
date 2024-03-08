-- Timestamps that cannot be guaranteed to occur may be null to indicate that they didn't (or haven't yet)

ALTER TABLE channel_log_dump MODIFY end_timestamp INT UNSIGNED NULL;
ALTER TABLE channel_log_dump MODIFY notified_user_count SMALLINT UNSIGNED NULL;

ALTER TABLE activation_log_dump MODIFY config_start_timestamp INT UNSIGNED NULL;
ALTER TABLE activation_log_dump MODIFY config_end_timestamp INT UNSIGNED NULL;
ALTER TABLE activation_log_dump MODIFY getpost_start_timestamp INT UNSIGNED NULL;
ALTER TABLE activation_log_dump MODIFY getpost_end_timestamp INT UNSIGNED NULL;
ALTER TABLE activation_log_dump MODIFY notify_start_timestamp INT UNSIGNED NULL;
ALTER TABLE activation_log_dump MODIFY notify_end_timestamp INT UNSIGNED NULL;
ALTER TABLE activation_log_dump MODIFY end_timestamp INT UNSIGNED NULL;