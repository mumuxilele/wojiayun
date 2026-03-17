-- 添加customerID字段
ALTER TABLE visit_records ADD customerID VARCHAR(64) DEFAULT NULL COMMENT '客户ID' AFTER creator;
