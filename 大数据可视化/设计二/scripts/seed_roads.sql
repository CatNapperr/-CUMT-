-- 初始路段数据
-- 执行前请确保已先运行 scripts/init_db.sql

USE `traffic_db`;

INSERT INTO `road_segment` (`id`, `name`, `type`, `free_flow_speed`, `capacity`) VALUES
  (1, '徐贾快速路', 'expressway', 85, 7800),
  (2, '淮海东路', 'arterial', 60, 4200),
  (3, '中山北路', 'arterial', 50, 3600),
  (4, '泉山南路', 'branch', 35, 1800),
  (5, '贾汪连接线', 'branch', 40, 2200),
  (6, '丰县东环路', 'branch', 45, 2000),
  (7, '沛县迎宾大道', 'arterial', 55, 3200),
  (8, '邳州运河路', 'arterial', 50, 3400),
  (9, '睢宁中央大街', 'arterial', 48, 3000),
  (10, '新沂新安大道', 'arterial', 52, 3300)
ON DUPLICATE KEY UPDATE
  `name` = VALUES(`name`),
  `type` = VALUES(`type`),
  `free_flow_speed` = VALUES(`free_flow_speed`),
  `capacity` = VALUES(`capacity`);
