-- =====================================================================
-- AI 模拟面试助手 · 数据库设计（MySQL 8.0 / InnoDB / utf8mb4）
-- 设计原则：
--   1. 免登录用户数据仅存浏览器本地（需求决策），本库只存已登录用户的云端数据
--   2. 题库题目支持下架/删除，面试历史通过 session_question.question_snapshot 快照解耦
--   3. 简历软删除（is_deleted），满足隐私合规与"删除权"要求
--   4. 外键一律 RESTRICT，用户数据删除走应用层软删/匿名化，避免硬删破坏业务链
-- =====================================================================

-- ---------------------------------------------------------------------
-- 模块一：账户模块
-- ---------------------------------------------------------------------
CREATE TABLE `user` (
  `id`            BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '用户ID',
  `phone`         VARCHAR(20)     DEFAULT NULL COMMENT '手机号（唯一）',
  `email`         VARCHAR(128)    DEFAULT NULL COMMENT '邮箱（唯一）',
  `nickname`      VARCHAR(64)     NOT NULL DEFAULT '' COMMENT '昵称',
  `password_hash` VARCHAR(255)    NOT NULL DEFAULT '' COMMENT '密码哈希',
  `avatar_url`    VARCHAR(255)    DEFAULT NULL COMMENT '头像地址',
  `register_source` VARCHAR(16)   NOT NULL DEFAULT 'email' COMMENT '注册来源: email/phone/oauth',
  `status`        TINYINT         NOT NULL DEFAULT 1 COMMENT '1正常 0禁用',
  `created_at`    DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '注册时间',
  `last_login_at` DATETIME        DEFAULT NULL COMMENT '最近登录时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_phone` (`phone`),
  UNIQUE KEY `uk_email` (`email`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户表（仅已登录用户入库）';

CREATE TABLE `resume` (
  `id`             BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '简历ID',
  `user_id`        BIGINT UNSIGNED NOT NULL COMMENT '所属用户',
  `file_name`      VARCHAR(128)    NOT NULL DEFAULT '' COMMENT '原始文件名',
  `file_url`       VARCHAR(255)    NOT NULL DEFAULT '' COMMENT '文件存储地址（加密存储）',
  `parsed_content` JSON            DEFAULT NULL COMMENT 'AI解析后的结构化简历内容',
  `tech_tags`      JSON            DEFAULT NULL COMMENT '提取的技术栈标签数组',
  `is_deleted`     TINYINT         NOT NULL DEFAULT 0 COMMENT '软删除标记: 0有效 1已删',
  `uploaded_at`    DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '上传时间',
  `updated_at`     DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_user` (`user_id`, `is_deleted`),
  CONSTRAINT `fk_resume_user` FOREIGN KEY (`user_id`) REFERENCES `user` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户简历表';

-- ---------------------------------------------------------------------
-- 模块二：题库模块（运营后台 + 面试出题共用）
-- ---------------------------------------------------------------------
CREATE TABLE `question` (
  `id`               BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '题目ID',
  `question_type`    VARCHAR(20)     NOT NULL COMMENT '题型: algorithm/system_design/fundamental/behavioral/project_dig',
  `title`            VARCHAR(255)    NOT NULL DEFAULT '' COMMENT '题目标题',
  `content`          TEXT            NOT NULL COMMENT '题干内容',
  `difficulty`       TINYINT         NOT NULL DEFAULT 1 COMMENT '难度: 1初级 2中级 3高级',
  `reference_answer` TEXT            DEFAULT NULL COMMENT '参考答案/解题思路',
  `test_cases`       JSON            DEFAULT NULL COMMENT '算法题测试用例[{input,expected}]',
  `status`           TINYINT         NOT NULL DEFAULT 0 COMMENT '0草稿 1上架 2下架',
  `created_by`       BIGINT UNSIGNED DEFAULT NULL COMMENT '录入运营ID',
  `created_at`       DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at`       DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_type_status` (`question_type`, `status`),
  KEY `idx_difficulty` (`difficulty`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='题目表';

CREATE TABLE `question_tag` (
  `id`         BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `question_id` BIGINT UNSIGNED NOT NULL COMMENT '题目ID',
  `tag_name`   VARCHAR(32)     NOT NULL COMMENT '标签名（技术栈/知识点，如 Java、Redis、动态规划）',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_q_tag` (`question_id`, `tag_name`),
  KEY `idx_tag` (`tag_name`),
  CONSTRAINT `fk_tag_question` FOREIGN KEY (`question_id`) REFERENCES `question` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='题目标签表';

CREATE TABLE `position` (
  `id`          BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '岗位ID',
  `name`        VARCHAR(64)     NOT NULL COMMENT '岗位名（如 后端Java、前端、算法）',
  `code`        VARCHAR(32)     NOT NULL COMMENT '岗位编码',
  `description` VARCHAR(255)    DEFAULT NULL,
  `status`      TINYINT         NOT NULL DEFAULT 1 COMMENT '1启用 0停用',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_code` (`code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='岗位字典表';

-- ---------------------------------------------------------------------
-- 模块三：面试会话（核心业务链）
-- ---------------------------------------------------------------------
CREATE TABLE `interview_session` (
  `id`            BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '面试会话ID',
  `user_id`       BIGINT UNSIGNED NOT NULL COMMENT '用户ID',
  `resume_id`     BIGINT UNSIGNED DEFAULT NULL COMMENT '关联简历（可选，决定是否简历定制出题）',
  `position_id`   BIGINT UNSIGNED NOT NULL COMMENT '目标岗位',
  `difficulty`    TINYINT         NOT NULL DEFAULT 2 COMMENT '难度: 1初级 2中级 3高级',
  `duration_min`  SMALLINT        NOT NULL DEFAULT 45 COMMENT '面试时长(分钟)',
  `question_mix`  JSON            DEFAULT NULL COMMENT '题型构成配置 {algorithm:1, system_design:1, fundamental:5}',
  `status`        VARCHAR(16)     NOT NULL DEFAULT 'configured' COMMENT '状态机: configured>in_progress>completed/cancelled',
  `started_at`    DATETIME        DEFAULT NULL COMMENT '实际开始时间',
  `ended_at`      DATETIME        DEFAULT NULL COMMENT '实际结束时间',
  `overall_score` DECIMAL(5,1)    DEFAULT NULL COMMENT '总分(百分制)，面试完成后回填',
  `overall_comment` VARCHAR(500)  DEFAULT NULL COMMENT '简短评语，面试完成后回填',
  `created_at`    DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_user_created` (`user_id`, `created_at`),
  KEY `idx_status` (`status`),
  CONSTRAINT `fk_session_user` FOREIGN KEY (`user_id`) REFERENCES `user` (`id`),
  CONSTRAINT `fk_session_resume` FOREIGN KEY (`resume_id`) REFERENCES `resume` (`id`),
  CONSTRAINT `fk_session_position` FOREIGN KEY (`position_id`) REFERENCES `position` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='面试会话表（主表）';

CREATE TABLE `session_section` (
  `id`          BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '环节ID',
  `session_id`  BIGINT UNSIGNED NOT NULL COMMENT '所属面试',
  `section_type` VARCHAR(16)    NOT NULL COMMENT '环节类型: voice(语音问答)/coding(在线编程)/whiteboard(白板设计)',
  `sequence_no` TINYINT         NOT NULL COMMENT '环节序号，控制面试流程顺序',
  `status`      VARCHAR(16)     NOT NULL DEFAULT 'pending' COMMENT 'pending/in_progress/completed',
  `started_at`  DATETIME        DEFAULT NULL,
  `ended_at`    DATETIME        DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `idx_session_seq` (`session_id`, `sequence_no`),
  CONSTRAINT `fk_section_session` FOREIGN KEY (`session_id`) REFERENCES `interview_session` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='面试环节表（voice/coding/whiteboard）';

CREATE TABLE `session_question` (
  `id`                BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '面试题目实例ID',
  `session_id`        BIGINT UNSIGNED NOT NULL COMMENT '所属面试',
  `section_id`        BIGINT UNSIGNED DEFAULT NULL COMMENT '所属环节（voice环节可为空，先出题后挂环节）',
  `question_id`       BIGINT UNSIGNED DEFAULT NULL COMMENT '题库题目ID（动态生成题为NULL）',
  `question_snapshot` TEXT            NOT NULL COMMENT '题目内容快照，题库下架/删除不影响历史面试',
  `source`            VARCHAR(16)     NOT NULL DEFAULT 'builtin' COMMENT '题目来源: builtin/resume_custom/ai_generated',
  `sequence_no`       TINYINT         NOT NULL DEFAULT 0 COMMENT '面试内出题顺序',
  `created_at`        DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_session` (`session_id`),
  KEY `idx_section` (`section_id`),
  CONSTRAINT `fk_sq_session` FOREIGN KEY (`session_id`) REFERENCES `interview_session` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_sq_question` FOREIGN KEY (`question_id`) REFERENCES `question` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='面试题目实例表（快照解耦）';

CREATE TABLE `interview_dialogue` (
  `id`         BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '对话记录ID',
  `session_id` BIGINT UNSIGNED NOT NULL COMMENT '所属面试',
  `section_id` BIGINT UNSIGNED DEFAULT NULL COMMENT '所属环节（面试官开场白等可为空）',
  `speaker`    VARCHAR(16)     NOT NULL COMMENT '说话方: interviewer/candidate',
  `content`    TEXT            NOT NULL COMMENT '内容（语音回答为ASR转写文本）',
  `audio_url`  VARCHAR(255)    DEFAULT NULL COMMENT '音频地址（可选）',
  `created_at` DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_session_time` (`session_id`, `created_at`),
  CONSTRAINT `fk_dlg_session` FOREIGN KEY (`session_id`) REFERENCES `interview_session` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_dlg_section` FOREIGN KEY (`section_id`) REFERENCES `session_section` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='面试对话流水表（语音/文字问答）';

CREATE TABLE `coding_submission` (
  `id`                BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '提交记录ID',
  `session_id`        BIGINT UNSIGNED NOT NULL COMMENT '所属面试',
  `section_id`        BIGINT UNSIGNED NOT NULL COMMENT '所属编程环节',
  `session_question_id` BIGINT UNSIGNED DEFAULT NULL COMMENT '对应题目实例',
  `language`          VARCHAR(32)     NOT NULL DEFAULT '' COMMENT '编程语言（java/python/go等）',
  `code`              MEDIUMTEXT      NOT NULL COMMENT '用户代码（保留每次迭代）',
  `run_status`        VARCHAR(16)     NOT NULL DEFAULT 'pending' COMMENT 'pending/running/success/error/timeout',
  `run_result`        JSON            DEFAULT NULL COMMENT '运行结果 {passed, failed, output, cases}',
  `submitted_at`      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_session` (`session_id`),
  CONSTRAINT `fk_coding_section` FOREIGN KEY (`section_id`) REFERENCES `session_section` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_coding_sq` FOREIGN KEY (`session_question_id`) REFERENCES `session_question` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='在线编程提交记录表（保留多次迭代历史）';

CREATE TABLE `whiteboard_snapshot` (
  `id`         BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '快照ID',
  `session_id` BIGINT UNSIGNED NOT NULL COMMENT '所属面试',
  `section_id` BIGINT UNSIGNED NOT NULL COMMENT '所属白板环节',
  `content`    JSON            NOT NULL COMMENT '白板画布数据（节点/连线/位置，Excalidraw格式）',
  `created_at` DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_section` (`section_id`),
  CONSTRAINT `fk_wb_section` FOREIGN KEY (`section_id`) REFERENCES `session_section` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='白板画布快照表（支持多版本自动保存）';

-- ---------------------------------------------------------------------
-- 模块四：评分反馈（简单打分为MVP，维度/逐题评分为会员扩展）
-- ---------------------------------------------------------------------
CREATE TABLE `session_evaluation` (
  `id`              BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '评估ID',
  `session_id`      BIGINT UNSIGNED NOT NULL COMMENT '所属面试（唯一，一面试一评估）',
  `total_score`     DECIMAL(5,1)    NOT NULL COMMENT '总分(百分制)',
  `overall_comment` VARCHAR(500)    NOT NULL DEFAULT '' COMMENT '简短评语',
  `eval_version`    VARCHAR(16)     NOT NULL DEFAULT 'v1' COMMENT '评分模型版本',
  `created_at`      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_session` (`session_id`),
  CONSTRAINT `fk_eval_session` FOREIGN KEY (`session_id`) REFERENCES `interview_session` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='面试评估主表（简单打分）';

CREATE TABLE `dimension_evaluation` (
  `id`         BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '维度评分ID',
  `session_id` BIGINT UNSIGNED NOT NULL COMMENT '所属面试',
  `dimension`  VARCHAR(20)     NOT NULL COMMENT '维度: algorithm/system_design/expression/code_quality/project_depth',
  `score`      DECIMAL(5,1)    NOT NULL COMMENT '该维度得分',
  `feedback`   VARCHAR(500)    DEFAULT NULL COMMENT '维度点评/改进建议',
  `created_at` DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_session_dim` (`session_id`, `dimension`),
  CONSTRAINT `fk_dim_eval` FOREIGN KEY (`session_id`) REFERENCES `interview_session` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='维度评分表（会员扩展）';

CREATE TABLE `question_evaluation` (
  `id`                 BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '逐题评估ID',
  `session_id`         BIGINT UNSIGNED NOT NULL COMMENT '所属面试',
  `session_question_id` BIGINT UNSIGNED NOT NULL COMMENT '题目实例',
  `score`              DECIMAL(5,1)    NOT NULL COMMENT '本题得分',
  `feedback`           VARCHAR(500)    DEFAULT NULL COMMENT '本题点评',
  `reference_compare`  TEXT            DEFAULT NULL COMMENT '与参考答案对比分析',
  `created_at`         DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_sq` (`session_question_id`),
  CONSTRAINT `fk_qe_session` FOREIGN KEY (`session_id`) REFERENCES `interview_session` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_qe_sq` FOREIGN KEY (`session_question_id`) REFERENCES `session_question` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='逐题评估表（会员扩展）';

-- ---------------------------------------------------------------------
-- 模块五：订阅会员（商业化）
-- ---------------------------------------------------------------------
CREATE TABLE `subscription_plan` (
  `id`          BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '套餐ID',
  `plan_code`   VARCHAR(32)     NOT NULL COMMENT '套餐编码（如 monthly/quarterly/yearly）',
  `name`        VARCHAR(64)     NOT NULL COMMENT '套餐名',
  `period_type` VARCHAR(16)     NOT NULL COMMENT '周期: monthly/quarterly/yearly',
  `price`       DECIMAL(10,2)   NOT NULL COMMENT '售价(元)',
  `original_price` DECIMAL(10,2) DEFAULT NULL COMMENT '划线原价',
  `description` VARCHAR(255)    DEFAULT NULL,
  `status`      TINYINT         NOT NULL DEFAULT 1 COMMENT '1在售 0停售',
  `sort`        INT             NOT NULL DEFAULT 0 COMMENT '展示排序',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_code` (`plan_code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='会员套餐表';

CREATE TABLE `payment_order` (
  `id`            BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '订单ID',
  `order_no`      VARCHAR(32)     NOT NULL COMMENT '业务订单号',
  `user_id`       BIGINT UNSIGNED NOT NULL COMMENT '下单用户',
  `plan_id`       BIGINT UNSIGNED NOT NULL COMMENT '购买套餐',
  `amount`        DECIMAL(10,2)   NOT NULL COMMENT '实付金额',
  `pay_channel`   VARCHAR(16)     DEFAULT NULL COMMENT '支付渠道: wechat/alipay',
  `status`        VARCHAR(16)     NOT NULL DEFAULT 'pending' COMMENT 'pending/paid/failed/refunded',
  `transaction_id` VARCHAR(64)    DEFAULT NULL COMMENT '支付平台流水号',
  `paid_at`       DATETIME        DEFAULT NULL COMMENT '支付时间',
  `created_at`    DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_order_no` (`order_no`),
  KEY `idx_user` (`user_id`),
  KEY `idx_status` (`status`),
  CONSTRAINT `fk_order_user` FOREIGN KEY (`user_id`) REFERENCES `user` (`id`),
  CONSTRAINT `fk_order_plan` FOREIGN KEY (`plan_id`) REFERENCES `subscription_plan` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='支付订单表';

CREATE TABLE `user_subscription` (
  `id`          BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '订阅记录ID',
  `user_id`     BIGINT UNSIGNED NOT NULL COMMENT '用户',
  `plan_id`     BIGINT UNSIGNED NOT NULL COMMENT '套餐',
  `order_id`    BIGINT UNSIGNED NOT NULL COMMENT '来源订单（一单对应一条订阅记录）',
  `start_time`  DATETIME        NOT NULL COMMENT '生效时间',
  `end_time`    DATETIME        NOT NULL COMMENT '到期时间（权益判定依据）',
  `status`      VARCHAR(16)     NOT NULL DEFAULT 'active' COMMENT 'active/expired/cancelled',
  `auto_renew`  TINYINT         NOT NULL DEFAULT 0 COMMENT '是否自动续费',
  `created_at`  DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_order` (`order_id`),
  KEY `idx_user_status` (`user_id`, `status`),
  KEY `idx_end_time` (`end_time`),
  CONSTRAINT `fk_sub_user` FOREIGN KEY (`user_id`) REFERENCES `user` (`id`),
  CONSTRAINT `fk_sub_plan` FOREIGN KEY (`plan_id`) REFERENCES `subscription_plan` (`id`),
  CONSTRAINT `fk_sub_order` FOREIGN KEY (`order_id`) REFERENCES `payment_order` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户订阅记录表（会员权益）';

CREATE TABLE `user_quota` (
  `id`          BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '配额记录ID',
  `user_id`     BIGINT UNSIGNED NOT NULL COMMENT '用户',
  `quota_month` CHAR(7)         NOT NULL COMMENT '配额月份 YYYY-MM',
  `used_count`  INT             NOT NULL DEFAULT 0 COMMENT '当月已用场次',
  `quota_limit` INT             NOT NULL DEFAULT 3 COMMENT '当月免费场次上限（会员不扣减）',
  `updated_at`  DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_user_month` (`user_id`, `quota_month`),
  CONSTRAINT `fk_quota_user` FOREIGN KEY (`user_id`) REFERENCES `user` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户月度面试配额表（防刷与成本控制）';
