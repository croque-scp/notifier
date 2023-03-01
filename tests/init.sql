CREATE USER 'root'@'%' IDENTIFIED BY 'root';
UPDATE mysql.user SET host = '%' WHERE user='root';
CREATE DATABASE IF NOT EXISTS `wikidot_notifier` CHARACTER SET utf8mb4 COLLATE utf8mb4_bin;
CREATE DATABASE IF NOT EXISTS `wikidot_notifier_test` CHARACTER SET utf8mb4 COLLATE utf8mb4_bin;
GRANT ALL PRIVILEGES ON `wikidot_notifier_test`.% TO 'root'@'*';

FLUSH PRIVILEGES;