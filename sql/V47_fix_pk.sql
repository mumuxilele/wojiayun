-- V47.0 修复主键为fid
-- 需要逐个表执行，因为可能有外键约束

-- business_applications
ALTER TABLE business_applications DROP PRIMARY KEY;
ALTER TABLE business_applications ADD PRIMARY KEY (fid);
ALTER TABLE business_applications ADD UNIQUE INDEX uk_id (id);

-- business_orders
ALTER TABLE business_orders DROP PRIMARY KEY;
ALTER TABLE business_orders ADD PRIMARY KEY (fid);
ALTER TABLE business_orders ADD UNIQUE INDEX uk_id (id);

-- business_reviews
ALTER TABLE business_reviews DROP PRIMARY KEY;
ALTER TABLE business_reviews ADD PRIMARY KEY (fid);
ALTER TABLE business_reviews ADD UNIQUE INDEX uk_id (id);

-- business_members
ALTER TABLE business_members DROP PRIMARY KEY;
ALTER TABLE business_members ADD PRIMARY KEY (fid);
ALTER TABLE business_members ADD UNIQUE INDEX uk_id (id);

-- business_feedback
ALTER TABLE business_feedback DROP PRIMARY KEY;
ALTER TABLE business_feedback ADD PRIMARY KEY (fid);
ALTER TABLE business_feedback ADD UNIQUE INDEX uk_id (id);

-- business_products
ALTER TABLE business_products DROP PRIMARY KEY;
ALTER TABLE business_products ADD PRIMARY KEY (fid);
ALTER TABLE business_products ADD UNIQUE INDEX uk_id (id);

-- business_coupons
ALTER TABLE business_coupons DROP PRIMARY KEY;
ALTER TABLE business_coupons ADD PRIMARY KEY (fid);
ALTER TABLE business_coupons ADD UNIQUE INDEX uk_id (id);

-- business_user_coupons
ALTER TABLE business_user_coupons DROP PRIMARY KEY;
ALTER TABLE business_user_coupons ADD PRIMARY KEY (fid);
ALTER TABLE business_user_coupons ADD UNIQUE INDEX uk_id (id);

-- business_approve_nodes
ALTER TABLE business_approve_nodes DROP PRIMARY KEY;
ALTER TABLE business_approve_nodes ADD PRIMARY KEY (fid);
ALTER TABLE business_approve_nodes ADD UNIQUE INDEX uk_id (id);

-- business_application_attachments
ALTER TABLE business_application_attachments DROP PRIMARY KEY;
ALTER TABLE business_application_attachments ADD PRIMARY KEY (fid);
ALTER TABLE business_application_attachments ADD UNIQUE INDEX uk_id (id);

-- business_application_reminds
ALTER TABLE business_application_reminds DROP PRIMARY KEY;
ALTER TABLE business_application_reminds ADD PRIMARY KEY (fid);
ALTER TABLE business_application_reminds ADD UNIQUE INDEX uk_id (id);

-- visit_records
ALTER TABLE visit_records DROP PRIMARY KEY;
ALTER TABLE visit_records ADD PRIMARY KEY (fid);
ALTER TABLE visit_records ADD UNIQUE INDEX uk_id (id);

-- chat_messages
ALTER TABLE chat_messages DROP PRIMARY KEY;
ALTER TABLE chat_messages ADD PRIMARY KEY (fid);
ALTER TABLE chat_messages ADD UNIQUE INDEX uk_id (id);

-- chat_sessions
ALTER TABLE chat_sessions DROP PRIMARY KEY;
ALTER TABLE chat_sessions ADD PRIMARY KEY (fid);
ALTER TABLE chat_sessions ADD UNIQUE INDEX uk_id (id);

-- auth_accounts
ALTER TABLE auth_accounts DROP PRIMARY KEY;
ALTER TABLE auth_accounts ADD PRIMARY KEY (fid);
ALTER TABLE auth_accounts ADD UNIQUE INDEX uk_id (id);
