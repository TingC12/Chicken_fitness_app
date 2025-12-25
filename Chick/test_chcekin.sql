-- 進 MySQL 後，先選資料庫
USE chicken_db;

-- 看看剛才那筆（確認 id、時間）
SELECT id, user_id, status, started_at, ended_at
FROM checkins
WHERE id = 2;

-- 把開始時間往前 31 分鐘（用 UTC 對齊後端）
UPDATE checkins
SET started_at = DATE_SUB(UTC_TIMESTAMP(), INTERVAL 31 MINUTE)
WHERE id = 2;
