-- MySQL 8.0 初始化脚本
-- 目标：创建交通历史数据数据库，仅用于存储 5 分钟粒度的历史采样点

CREATE DATABASE IF NOT EXISTS `traffic_db`
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_0900_ai_ci;

USE `traffic_db`;

CREATE TABLE IF NOT EXISTS `road_segment` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `name` VARCHAR(50) NOT NULL,
  `type` ENUM('expressway', 'arterial', 'branch') NOT NULL,
  `free_flow_speed` INT NOT NULL COMMENT 'km/h',
  `capacity` INT NOT NULL COMMENT 'veh/h',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS `traffic_history` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `road_id` INT NOT NULL,
  `timestamp` DATETIME NOT NULL,
  `volume` INT NOT NULL COMMENT 'veh/5min',
  `speed` DECIMAL(5,2) NOT NULL COMMENT 'km/h',
  `occupancy` DECIMAL(4,2) NOT NULL COMMENT '%',
  PRIMARY KEY (`id`),
  KEY `idx_traffic_history_road_timestamp` (`road_id`, `timestamp`),
  CONSTRAINT `fk_traffic_history_road`
    FOREIGN KEY (`road_id`) REFERENCES `road_segment` (`id`)
    ON UPDATE CASCADE
    ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
