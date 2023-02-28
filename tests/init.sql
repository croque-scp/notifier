CREATE USER IF NOT EXISTS 'root'@'%' IDENTIFIED BY 'root';
CREATE DATABASE IF NOT EXISTS `wikidot_notifier_test` CHARACTER SET utf8mb4 COLLATE utf8mb4_bin;
GRANT ALL PRIVILEGES ON `wikidot_notifier_test`.% TO 'root'@'*';

FLUSH PRIVILEGES;