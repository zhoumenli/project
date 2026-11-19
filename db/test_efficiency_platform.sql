-- =====================================================================
-- 测试效能平台 (Test Efficiency Platform) — 数据库初始化脚本
-- ---------------------------------------------------------------------
-- 用途：在 Navicat / MySQL 中一键创建平台数据库与全部业务表
-- 数据库：test_efficiency_platform
-- 字符集：utf8mb4 / utf8mb4_unicode_ci   引擎：InnoDB
-- MySQL：8.0+ （兼容 5.7，SQL 语法向下兼容）
-- 表数量：10 张
-- ---------------------------------------------------------------------
-- 【导入方式】
--   方式一（Navicat 图形化）
--     1) 新建 MySQL 连接：主机 127.0.0.1，端口 3306，用户 root，密码 root
--     2) 右键连接 -> 运行 SQL 文件 -> 选择本文件 -> 开始
--     3) 刷新连接，即可看到 test_efficiency_platform 库
--   方式二（命令行）
--     mysql -uroot -proot < test_efficiency_platform.sql
--   方式三（已存在该库时覆盖）
--     mysql -uroot -proot -D test_efficiency_platform < test_efficiency_platform.sql
-- ---------------------------------------------------------------------
-- 【说明】
--   * ⚠️ 警告：脚本使用 DROP TABLE IF EXISTS，重复执行会【清空并重建】test_efficiency_platform
--     库中的全部数据（包括你在平台上创建的项目/用例/执行记录）——请勿在有真实业务数据的库上执行
--   * auth_tokens 表只建表不写入数据（登录令牌为运行时签发，不应固化在脚本中）
--   * 用户密码以 PBKDF2-HMAC-SHA256（210,000 次迭代 + 随机盐）哈希存储，非明文
-- ---------------------------------------------------------------------
-- 【演示账号】
--   用户名：testuser
--   密码  ：Test@1234
--   规则  ：用户名 3-20 位字母/数字/下划线；密码 8-32 位且需含大写+小写+数字
-- =====================================================================


-- ---------------------------------------------------------------------
-- 0. 建库并切换
-- ---------------------------------------------------------------------
CREATE DATABASE IF NOT EXISTS `test_efficiency_platform`
  DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE `test_efficiency_platform`;

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- ---------------------------------------------------------------------
-- 1. 清理旧表（保证脚本可重复执行）
-- ---------------------------------------------------------------------
DROP TABLE IF EXISTS `run_details`;
DROP TABLE IF EXISTS `runs`;
DROP TABLE IF EXISTS `cases`;
DROP TABLE IF EXISTS `folders`;
DROP TABLE IF EXISTS `suites`;
DROP TABLE IF EXISTS `environments`;
DROP TABLE IF EXISTS `generation_records`;
DROP TABLE IF EXISTS `auth_tokens`;
DROP TABLE IF EXISTS `projects`;
DROP TABLE IF EXISTS `users`;

-- ---------------------------------------------------------------------
-- 2. 建表（建表阶段保持外键检查关闭，因为存在循环引用顺序）
-- ---------------------------------------------------------------------

CREATE TABLE `auth_tokens` (

  `id` int NOT NULL AUTO_INCREMENT,
  `token` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL,
  `user_id` int NOT NULL,
  `created_at` datetime DEFAULT NULL,
  `expires_at` datetime DEFAULT NULL,
  `last_active_at` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `ix_auth_tokens_token` (`token`),
  KEY `user_id` (`user_id`),
  KEY `ix_auth_tokens_id` (`id`),
  CONSTRAINT `auth_tokens_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE

) ENGINE=InnoDB AUTO_INCREMENT=8 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `cases` (

  `id` int NOT NULL AUTO_INCREMENT,
  `folder_id` int NOT NULL,
  `title` varchar(200) COLLATE utf8mb4_unicode_ci NOT NULL,
  `case_type` varchar(20) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `priority` varchar(10) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `tags` json DEFAULT NULL,
  `precondition` text COLLATE utf8mb4_unicode_ci,
  `steps` text COLLATE utf8mb4_unicode_ci,
  `expected` text COLLATE utf8mb4_unicode_ci,
  `method` varchar(10) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `url` text COLLATE utf8mb4_unicode_ci,
  `headers` json DEFAULT NULL,
  `body` text COLLATE utf8mb4_unicode_ci,
  `assertions` json DEFAULT NULL,
  `extractors` json DEFAULT NULL,
  `ui_config` json DEFAULT NULL,
  `enabled` tinyint(1) DEFAULT NULL,
  `created_at` datetime DEFAULT NULL,
  `updated_at` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `folder_id` (`folder_id`),
  KEY `ix_cases_id` (`id`),
  CONSTRAINT `cases_ibfk_1` FOREIGN KEY (`folder_id`) REFERENCES `folders` (`id`) ON DELETE CASCADE

) ENGINE=InnoDB AUTO_INCREMENT=8 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `environments` (

  `id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  `base_url` text COLLATE utf8mb4_unicode_ci,
  `variables` json DEFAULT NULL,
  `created_at` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `ix_environments_id` (`id`)

) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `folders` (

  `id` int NOT NULL AUTO_INCREMENT,
  `project_id` int NOT NULL,
  `parent_id` int DEFAULT NULL,
  `name` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  `created_at` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `project_id` (`project_id`),
  KEY `parent_id` (`parent_id`),
  KEY `ix_folders_id` (`id`),
  CONSTRAINT `folders_ibfk_1` FOREIGN KEY (`project_id`) REFERENCES `projects` (`id`) ON DELETE CASCADE,
  CONSTRAINT `folders_ibfk_2` FOREIGN KEY (`parent_id`) REFERENCES `folders` (`id`) ON DELETE CASCADE

) ENGINE=InnoDB AUTO_INCREMENT=4 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `generation_records` (

  `id` int NOT NULL AUTO_INCREMENT,
  `project_id` int DEFAULT NULL,
  `doc_name` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  `doc_format` varchar(30) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `doc_size` int DEFAULT NULL,
  `backend` varchar(20) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `requirement_text` text COLLATE utf8mb4_unicode_ci,
  `cases_count` int DEFAULT NULL,
  `dimensions` json DEFAULT NULL,
  `cases` json DEFAULT NULL,
  `imported` tinyint(1) DEFAULT NULL,
  `created_at` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `project_id` (`project_id`),
  KEY `ix_generation_records_id` (`id`),
  CONSTRAINT `generation_records_ibfk_1` FOREIGN KEY (`project_id`) REFERENCES `projects` (`id`) ON DELETE CASCADE

) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `projects` (

  `id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  `description` text COLLATE utf8mb4_unicode_ci,
  `created_at` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `ix_projects_id` (`id`)

) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `run_details` (

  `id` int NOT NULL AUTO_INCREMENT,
  `run_id` int NOT NULL,
  `case_id` int DEFAULT NULL,
  `case_title` varchar(200) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `case_type` varchar(20) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `status` varchar(20) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `duration_ms` int DEFAULT NULL,
  `error_msg` text COLLATE utf8mb4_unicode_ci,
  `request_info` json DEFAULT NULL,
  `response_info` json DEFAULT NULL,
  `assertions_result` json DEFAULT NULL,
  `extracted` json DEFAULT NULL,
  `logs` text COLLATE utf8mb4_unicode_ci,
  `created_at` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `run_id` (`run_id`),
  KEY `case_id` (`case_id`),
  KEY `ix_run_details_id` (`id`),
  CONSTRAINT `run_details_ibfk_1` FOREIGN KEY (`run_id`) REFERENCES `runs` (`id`) ON DELETE CASCADE,
  CONSTRAINT `run_details_ibfk_2` FOREIGN KEY (`case_id`) REFERENCES `cases` (`id`) ON DELETE SET NULL

) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `runs` (

  `id` int NOT NULL AUTO_INCREMENT,
  `suite_id` int DEFAULT NULL,
  `env_id` int DEFAULT NULL,
  `status` varchar(20) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `trigger` varchar(20) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `total` int DEFAULT NULL,
  `passed` int DEFAULT NULL,
  `failed` int DEFAULT NULL,
  `skipped` int DEFAULT NULL,
  `start_time` datetime DEFAULT NULL,
  `end_time` datetime DEFAULT NULL,
  `results` json DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `suite_id` (`suite_id`),
  KEY `env_id` (`env_id`),
  KEY `ix_runs_id` (`id`),
  CONSTRAINT `runs_ibfk_1` FOREIGN KEY (`suite_id`) REFERENCES `suites` (`id`) ON DELETE SET NULL,
  CONSTRAINT `runs_ibfk_2` FOREIGN KEY (`env_id`) REFERENCES `environments` (`id`) ON DELETE SET NULL

) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `suites` (

  `id` int NOT NULL AUTO_INCREMENT,
  `project_id` int NOT NULL,
  `name` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  `case_ids` json DEFAULT NULL,
  `env_id` int DEFAULT NULL,
  `created_at` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `project_id` (`project_id`),
  KEY `env_id` (`env_id`),
  KEY `ix_suites_id` (`id`),
  CONSTRAINT `suites_ibfk_1` FOREIGN KEY (`project_id`) REFERENCES `projects` (`id`) ON DELETE CASCADE,
  CONSTRAINT `suites_ibfk_2` FOREIGN KEY (`env_id`) REFERENCES `environments` (`id`) ON DELETE SET NULL

) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `users` (

  `id` int NOT NULL AUTO_INCREMENT,
  `username` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL,
  `password_hash` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  `role` varchar(20) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `created_at` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `ix_users_username` (`username`),
  KEY `ix_users_id` (`id`)

) ENGINE=InnoDB AUTO_INCREMENT=3 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

SET FOREIGN_KEY_CHECKS = 1;

-- ---------------------------------------------------------------------
-- 3. 种子数据（演示账号 + 示例项目/环境/测试集/用例）
-- ---------------------------------------------------------------------

INSERT INTO `users` VALUES (1,'testuser','pbkdf2_sha256$210000$b99c6713f3a674445a459bbd0c19ac4d$3a6d099bcab1d547c4a21925a557a01538b6d75492e8d0dd5b07ec5c04e0adbb','user','2026-11-19 16:41:37');

INSERT INTO `projects` (`id`, `name`, `description`, `created_at`) VALUES (1,'电商系统','Web + 接口测试演示项目','2026-11-19 16:41:28');

INSERT INTO `environments` (`id`, `name`, `base_url`, `variables`, `created_at`) VALUES (1,'本地 Mock','http://127.0.0.1:9001','{\"page\": \"1\", \"token\": \"demo-token\"}','2026-11-19 16:41:28');

INSERT INTO `suites` (`id`, `project_id`, `name`, `case_ids`, `env_id`, `created_at`) VALUES (1,1,'接口冒烟测试集','[1, 2, 3, 4, 5]',1,'2026-11-19 16:41:28');

INSERT INTO `folders` (`id`, `project_id`, `parent_id`, `name`, `created_at`) VALUES (1,1,NULL,'用户模块','2026-11-19 16:41:28'),(2,1,NULL,'商品模块','2026-11-19 16:41:28'),(3,1,NULL,'登录相关','2026-11-19 16:41:28');

INSERT INTO `cases` (`id`, `folder_id`, `title`, `case_type`, `priority`, `tags`, `precondition`, `steps`, `expected`, `method`, `url`, `headers`, `body`, `assertions`, `extractors`, `ui_config`, `enabled`, `created_at`, `updated_at`) VALUES (1,3,'登录成功 - 正确账号密码','api','P0','[\"登录\", \"冒烟\"]','','','返回 200，code=0，提取 token','POST','/api/login','{\"Content-Type\": \"application/json\"}','{\"username\":\"admin\",\"password\":\"123456\"}','[{\"op\": \"eq\", \"type\": \"status\", \"value\": \"200\"}, {\"op\": \"eq\", \"key\": \"code\", \"type\": \"json\", \"value\": \"0\"}]','[{\"key\": \"data.token\", \"name\": \"token\", \"source\": \"json\"}]','{}',1,'2026-11-19 16:41:28','2026-11-19 16:41:28'),(2,3,'登录失败 - 错误密码','api','P1','[\"登录\", \"异常\"]','','','','POST','/api/login','{\"Content-Type\": \"application/json\"}','{\"username\":\"admin\",\"password\":\"wrong\"}','[{\"op\": \"eq\", \"key\": \"code\", \"type\": \"json\", \"value\": \"401\"}]','[]','{}',1,'2026-11-19 16:41:28','2026-11-19 16:41:28'),(3,1,'获取用户信息','api','P1','[\"用户\"]','','','','GET','/api/user/info','{\"Authorization\": \"Bearer {{token}}\"}','','[{\"op\": \"eq\", \"type\": \"status\", \"value\": \"200\"}]','[]','{}',1,'2026-11-19 16:41:28','2026-11-19 16:41:28'),(4,2,'商品列表 - 分页查询','api','P1','[\"商品\"]','','','','GET','/api/products?page=1&size=10','{}','','[{\"op\": \"eq\", \"type\": \"status\", \"value\": \"200\"}, {\"op\": \"gte\", \"key\": \"data.length\", \"type\": \"json\", \"value\": \"5\"}]','[]','{}',1,'2026-11-19 16:41:28','2026-11-19 16:41:28'),(5,2,'搜索商品 - 关键字为空','api','P2','[\"商品\", \"异常\"]','','','','GET','/api/products?keyword=','{}','','[{\"op\": \"eq\", \"type\": \"status\", \"value\": \"200\"}]','[]','{}',1,'2026-11-19 16:41:28','2026-11-19 16:41:28'),(6,1,'用户登录 UI 流程','ui','P0','[\"登录\", \"冒烟\"]','','[{\"action\":\"goto\",\"target\":\"https://example.com/login\"},{\"action\":\"fill\",\"target\":\"#username\",\"value\":\"admin\"},{\"action\":\"fill\",\"target\":\"#password\",\"value\":\"123456\"},{\"action\":\"click\",\"target\":\"button[type=submit]\"},{\"action\":\"assert_visible\",\"target\":\".dashboard\",\"screenshot\":true}]','登录后跳转首页并截图','GET','','{}','','[]','[]','{}',1,'2026-11-19 16:41:28','2026-11-19 16:41:28'),(7,2,'手工探索 - 商品详情页展示','manual','P2','[\"探索\"]','已登录','1. 打开商品详情\n2. 检查图片与价格','信息展示正确','GET','','{}','','[]','[]','{}',1,'2026-11-19 16:41:28','2026-11-19 16:41:28');


-- ---------------------------------------------------------------------
-- 4. 自检：确认表结构已就位
-- ---------------------------------------------------------------------
SELECT TABLE_NAME AS '表名', TABLE_COMMENT AS '说明'
  FROM information_schema.TABLES
 WHERE TABLE_SCHEMA = 'test_efficiency_platform'
 ORDER BY TABLE_NAME;

SELECT id, username, role, created_at FROM users;


-- =====================================================================
-- 初始化完成。
-- 后端连接配置（backend/app/database.py，默认已按此设置）：
--   DB_BACKEND=mysql
--   DB_HOST=127.0.0.1
--   DB_PORT=3306
--   DB_NAME=test_efficiency_platform
--   DB_USER=root
--   DB_PASSWORD=root
-- =====================================================================
