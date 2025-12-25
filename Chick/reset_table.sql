USE chicken_db;
SET FOREIGN_KEY_CHECKS = 0;

TRUNCATE TABLE `coins_ledger`;
TRUNCATE TABLE `checkins`;
TRUNCATE TABLE `runs`;
TRUNCATE TABLE `refresh_tokens`;
TRUNCATE TABLE `users`;          -- 若 users 被其他表外鍵參照，放最後

SET FOREIGN_KEY_CHECKS = 1;
