-- =============================================
-- 智慧工单系统一期 - 数据库迁移脚本
-- 版本: V1.0
-- 日期: 2026-05-12
-- 说明: 基于智慧工单项目一期立项需求清单创建
-- =============================================

-- =============================================
-- 1. 工单分类表 (支持多级分类)
-- =============================================
CREATE TABLE IF NOT EXISTS t_wo_category (
    fid VARCHAR(64) PRIMARY KEY COMMENT '分类ID',
    fec_id VARCHAR(64) NOT NULL COMMENT '企业ID',
    fproject_id VARCHAR(64) NOT NULL COMMENT '项目ID',
    fparent_id VARCHAR(64) DEFAULT NULL COMMENT '父分类ID(NULL=顶级)',
    fcategory_name VARCHAR(100) NOT NULL COMMENT '分类名称',
    fcategory_code VARCHAR(50) NOT NULL COMMENT '分类编码',
    fcategory_type VARCHAR(30) NOT NULL COMMENT '分类类型: quality=品质检查 equipment=设备巡查 comprehensive=综合巡查 repair=报事报修 other=其他',
    ficon VARCHAR(200) DEFAULT NULL COMMENT '分类图标URL',
    fsort_order INT DEFAULT 0 COMMENT '排序号',
    fdescription TEXT DEFAULT NULL COMMENT '分类描述',
    fis_enabled INT DEFAULT 1 COMMENT '是否启用: 0=禁用 1=启用',
    fcreate_user_id VARCHAR(64) DEFAULT NULL COMMENT '创建人ID',
    create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    update_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    delete_time DATETIME DEFAULT NULL COMMENT '删除时间',
    is_deleted INT DEFAULT 0 COMMENT '软删除: 0=未删 1=已删',
    INDEX idx_fec_id (fec_id),
    INDEX idx_project_id (fproject_id),
    INDEX idx_parent_id (fparent_id),
    INDEX idx_type (fcategory_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='工单分类表';

-- =============================================
-- 2. 工单模板表 (标准周期工单模板)
-- =============================================
CREATE TABLE IF NOT EXISTS t_wo_template (
    fid VARCHAR(64) PRIMARY KEY COMMENT '模板ID',
    fec_id VARCHAR(64) NOT NULL COMMENT '企业ID',
    fproject_id VARCHAR(64) NOT NULL COMMENT '项目ID',
    ftemplate_name VARCHAR(200) NOT NULL COMMENT '模板名称',
    ftemplate_code VARCHAR(50) NOT NULL COMMENT '模板编号',
    fcategory_id VARCHAR(64) NOT NULL COMMENT '关联分类ID',
    fwo_type VARCHAR(30) NOT NULL COMMENT '工单类型: quality=品质检查 equipment=设备巡查 comprehensive=综合巡查',
    fdescription TEXT DEFAULT NULL COMMENT '模板描述',
    -- 巡检范围
    fscope_type VARCHAR(20) DEFAULT 'project' COMMENT '范围类型: project=全项目 building=楼栋 area=区域 equipment=指定设备',
    fscope_config TEXT DEFAULT NULL COMMENT '范围配置(JSON: 楼栋/区域/设备ID列表)',
    -- 执行周期
    fcycle_type VARCHAR(20) NOT NULL COMMENT '周期类型: daily=每日 weekly=每周 monthly=每月 quarterly=每季度 custom=自定义',
    fcycle_value INT DEFAULT 1 COMMENT '周期数值(如每周几=1-7, 每月几号=1-31)',
    fexecute_time VARCHAR(10) DEFAULT '08:00' COMMENT '执行时间点(HH:MM)',
    -- SLA
    fsla_level VARCHAR(10) DEFAULT 'L3' COMMENT '默认SLA等级: L1/L2/L3/L4',
    fresponse_minutes INT DEFAULT 60 COMMENT '响应时限(分钟)',
    fcomplete_hours INT DEFAULT 8 COMMENT '完成时限(小时)',
    -- 执行人
    fexecutor_type VARCHAR(20) DEFAULT 'assign' COMMENT '执行人类型: assign=指定 role=按角色 auto=自动分配',
    fexecutor_config TEXT DEFAULT NULL COMMENT '执行人配置(JSON: 用户ID列表或角色列表)',
    -- 状态
    fstatus VARCHAR(20) DEFAULT 'active' COMMENT '状态: active=启用 inactive=停用 draft=草稿',
    fversion INT DEFAULT 1 COMMENT '版本号',
    fremark TEXT DEFAULT NULL COMMENT '备注',
    fcreate_user_id VARCHAR(64) DEFAULT NULL COMMENT '创建人ID',
    create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    update_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    delete_time DATETIME DEFAULT NULL COMMENT '删除时间',
    is_deleted INT DEFAULT 0 COMMENT '软删除: 0=未删 1=已删',
    INDEX idx_fec_id (fec_id),
    INDEX idx_project_id (fproject_id),
    INDEX idx_category_id (fcategory_id),
    INDEX idx_type (fwo_type),
    INDEX idx_status (fstatus)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='工单模板表';

-- =============================================
-- 3. 模板检查项表
-- =============================================
CREATE TABLE IF NOT EXISTS t_wo_template_item (
    fid VARCHAR(64) PRIMARY KEY COMMENT '检查项ID',
    fec_id VARCHAR(64) NOT NULL COMMENT '企业ID',
    fproject_id VARCHAR(64) NOT NULL COMMENT '项目ID',
    ftemplate_id VARCHAR(64) NOT NULL COMMENT '所属模板ID',
    fitem_name VARCHAR(200) NOT NULL COMMENT '检查项名称',
    fitem_code VARCHAR(50) DEFAULT NULL COMMENT '检查项编码',
    fitem_type VARCHAR(20) DEFAULT 'check' COMMENT '检查项类型: check=勾选 score=评分 text=文本 input=输入 photo=拍照',
    fscore_weight DECIMAL(5,2) DEFAULT 0 COMMENT '评分权重',
    fpass_score DECIMAL(5,2) DEFAULT 60 COMMENT '合格分数',
    foptions TEXT DEFAULT NULL COMMENT '选项配置(JSON数组)',
    fsort_order INT DEFAULT 0 COMMENT '排序号',
    fis_required INT DEFAULT 1 COMMENT '是否必填: 0=否 1=是',
    fremark TEXT DEFAULT NULL COMMENT '备注说明',
    create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    update_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    delete_time DATETIME DEFAULT NULL COMMENT '删除时间',
    is_deleted INT DEFAULT 0 COMMENT '软删除: 0=未删 1=已删',
    INDEX idx_template_id (ftemplate_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='模板检查项表';

-- =============================================
-- 4. SLA规则表
-- =============================================
CREATE TABLE IF NOT EXISTS t_wo_sla_rule (
    fid VARCHAR(64) PRIMARY KEY COMMENT '规则ID',
    fec_id VARCHAR(64) NOT NULL COMMENT '企业ID',
    fproject_id VARCHAR(64) DEFAULT NULL COMMENT '项目ID(NULL=全局)',
    frule_name VARCHAR(100) NOT NULL COMMENT '规则名称',
    fsla_level VARCHAR(10) NOT NULL COMMENT 'SLA等级: L1/L2/L3/L4',
    fpriority INT DEFAULT 0 COMMENT '优先级(数字越大越高)',
    fresponse_minutes INT NOT NULL COMMENT '响应时限(分钟)',
    fcomplete_hours INT NOT NULL COMMENT '完成时限(小时)',
    fescalate_minutes INT DEFAULT NULL COMMENT '升级提醒时间(分钟)',
    fescalate_level INT DEFAULT 1 COMMENT '升级层级',
    foverdue_action VARCHAR(20) DEFAULT 'alert' COMMENT '超期动作: alert=提醒 escalate=升级 auto_close=自动关闭',
    fcolor VARCHAR(20) DEFAULT NULL COMMENT '显示颜色',
    fdescription TEXT DEFAULT NULL COMMENT '规则描述',
    fis_enabled INT DEFAULT 1 COMMENT '是否启用',
    fcreate_user_id VARCHAR(64) DEFAULT NULL COMMENT '创建人ID',
    create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    update_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    delete_time DATETIME DEFAULT NULL COMMENT '删除时间',
    is_deleted INT DEFAULT 0 COMMENT '软删除: 0=未删 1=已删',
    UNIQUE KEY uk_level_project (fsla_level, fproject_id, fec_id),
    INDEX idx_fec_id (fec_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='SLA规则表';

-- =============================================
-- 5. 派单规则表
-- =============================================
CREATE TABLE IF NOT EXISTS t_wo_dispatch_rule (
    fid VARCHAR(64) PRIMARY KEY COMMENT '规则ID',
    fec_id VARCHAR(64) NOT NULL COMMENT '企业ID',
    fproject_id VARCHAR(64) DEFAULT NULL COMMENT '项目ID(NULL=全局)',
    frule_name VARCHAR(100) NOT NULL COMMENT '规则名称',
    frule_type VARCHAR(30) NOT NULL COMMENT '规则类型: category=按分类 location=按位置 level=按优先级 time=按时段 keyword=按关键词',
    fmatch_condition TEXT NOT NULL COMMENT '匹配条件(JSON: 分类ID/位置/关键词等)',
    fdispatch_type VARCHAR(20) DEFAULT 'auto' COMMENT '派单方式: auto=自动 manual=手动 rotate=轮询',
    ftarget_type VARCHAR(20) DEFAULT 'user' COMMENT '目标类型: user=指定用户 role=指定角色 dept=指定部门',
    ftarget_config TEXT NOT NULL COMMENT '目标配置(JSON: 用户ID/角色ID/部门ID列表)',
    fpriority INT DEFAULT 0 COMMENT '规则优先级(数字越大越高)',
    fis_enabled INT DEFAULT 1 COMMENT '是否启用',
    fdescription TEXT DEFAULT NULL COMMENT '规则描述',
    fcreate_user_id VARCHAR(64) DEFAULT NULL COMMENT '创建人ID',
    create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    update_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    delete_time DATETIME DEFAULT NULL COMMENT '删除时间',
    is_deleted INT DEFAULT 0 COMMENT '软删除: 0=未删 1=已删',
    INDEX idx_fec_id (fec_id),
    INDEX idx_type (frule_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='派单规则表';

-- =============================================
-- 6. 工单流转节点定义表
-- =============================================
CREATE TABLE IF NOT EXISTS t_wo_flow_node (
    fid VARCHAR(64) PRIMARY KEY COMMENT '节点ID',
    fec_id VARCHAR(64) NOT NULL COMMENT '企业ID',
    fproject_id VARCHAR(64) DEFAULT NULL COMMENT '项目ID(NULL=全局)',
    fflow_name VARCHAR(100) NOT NULL COMMENT '流程名称',
    fwo_type VARCHAR(30) NOT NULL COMMENT '适用工单类型',
    fnode_code VARCHAR(50) NOT NULL COMMENT '节点编码',
    fnode_name VARCHAR(100) NOT NULL COMMENT '节点名称',
    fnode_type VARCHAR(20) NOT NULL COMMENT '节点类型: start=开始 task=任务审批=审批 end=结束 condition=条件',
    fsort_order INT DEFAULT 0 COMMENT '排序号',
    fassignee_type VARCHAR(20) DEFAULT NULL COMMENT '处理人类型: creator=创建人 dispatcher=派单人 assignee=执行人 reviewer=审核人',
    faction_required INT DEFAULT 1 COMMENT '是否需要操作: 0=自动 1=需要',
    ftimeout_minutes INT DEFAULT NULL COMMENT '超时时间(分钟)',
    ftimeout_action VARCHAR(20) DEFAULT NULL COMMENT '超时动作',
    fremark TEXT DEFAULT NULL COMMENT '备注',
    create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    update_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    delete_time DATETIME DEFAULT NULL COMMENT '删除时间',
    is_deleted INT DEFAULT 0 COMMENT '软删除: 0=未删 1=已删',
    INDEX idx_fec_id (fec_id),
    INDEX idx_flow_type (fflow_name, fwo_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='工单流转节点定义表';

-- =============================================
-- 7. 智慧工单主表 (增强版)
-- =============================================
CREATE TABLE IF NOT EXISTS t_smart_work_order (
    fid VARCHAR(64) PRIMARY KEY COMMENT '工单ID',
    fec_id VARCHAR(64) NOT NULL COMMENT '企业ID',
    fproject_id VARCHAR(64) NOT NULL COMMENT '项目ID',
    -- 工单基本信息
    fwo_no VARCHAR(50) NOT NULL COMMENT '工单编号(自动生成)',
    ftitle VARCHAR(300) NOT NULL COMMENT '工单标题',
    fdescription TEXT DEFAULT NULL COMMENT '工单描述',
    -- 分类与类型
    fcategory_id VARCHAR(64) DEFAULT NULL COMMENT '分类ID',
    fwo_type VARCHAR(30) NOT NULL COMMENT '工单类型: quality=品质检查 equipment=设备巡查 comprehensive=综合巡查 repair=报事报修 other=其他',
    fsub_type VARCHAR(50) DEFAULT NULL COMMENT '子类型',
    -- 来源
    fsource VARCHAR(20) DEFAULT 'manual' COMMENT '来源: manual=手动 system=系统自动 eba=EBA系统 ai=AI品控 complaint=投诉转 inspection=巡检转',
    fsource_id VARCHAR(64) DEFAULT NULL COMMENT '来源关联ID',
    -- 位置信息
    flocation_type VARCHAR(20) DEFAULT 'building' COMMENT '位置类型: building=楼栋 area=区域 equipment=设备 outdoor=室外',
    fbuilding_id VARCHAR(64) DEFAULT NULL COMMENT '楼栋ID',
    fbuilding_name VARCHAR(100) DEFAULT NULL COMMENT '楼栋名称',
    ffloor VARCHAR(20) DEFAULT NULL COMMENT '楼层',
    froom_number VARCHAR(32) DEFAULT NULL COMMENT '房间号',
    fequipment_id VARCHAR(64) DEFAULT NULL COMMENT '设备ID',
    fequipment_name VARCHAR(200) DEFAULT NULL COMMENT '设备名称',
    flocation_detail VARCHAR(500) DEFAULT NULL COMMENT '详细位置描述',
    -- 优先级与SLA
    fpriority VARCHAR(10) DEFAULT 'medium' COMMENT '优先级: urgent=紧急 high=高 medium=中 low=低',
    fsla_level VARCHAR(10) DEFAULT 'L3' COMMENT 'SLA等级: L1/L2/L3/L4',
    fsla_response_deadline DATETIME DEFAULT NULL COMMENT 'SLA响应截止时间',
    fsla_complete_deadline DATETIME DEFAULT NULL COMMENT 'SLA完成截止时间',
    -- 模板关联(标准周期工单)
    ftemplate_id VARCHAR(64) DEFAULT NULL COMMENT '模板ID',
    fplan_date DATE DEFAULT NULL COMMENT '计划执行日期',
    fplan_time VARCHAR(10) DEFAULT NULL COMMENT '计划执行时间',
    -- 状态流转
    fstatus VARCHAR(30) NOT NULL DEFAULT 'draft' COMMENT '状态: draft=草稿 pending_dispatch=待派单 dispatched=已派单 accepted=已接收 in_progress=执行中 completed=已完成 reviewing=审核中 closed=已关闭 cancelled=已取消 rejected=已驳回',
    fcurrent_node VARCHAR(50) DEFAULT NULL COMMENT '当前流转节点',
    -- 报单人信息
    freporter_id VARCHAR(64) DEFAULT NULL COMMENT '报单人ID',
    freporter_name VARCHAR(64) DEFAULT NULL COMMENT '报单人姓名',
    freporter_phone VARCHAR(20) DEFAULT NULL COMMENT '报单人电话',
    freporter_type VARCHAR(20) DEFAULT 'owner' COMMENT '报单人类型: owner=业主 tenant=租户 staff=员工 system=系统 visitor=访客',
    -- 联系人
    fcontact_name VARCHAR(64) DEFAULT NULL COMMENT '联系人姓名',
    fcontact_phone VARCHAR(20) DEFAULT NULL COMMENT '联系人电话',
    fcontact_time VARCHAR(50) DEFAULT NULL COMMENT '期望联系时间',
    -- 派单信息
    fdispatch_type VARCHAR(20) DEFAULT 'manual' COMMENT '派单方式: auto=自动 manual=手动',
    fdispatch_rule_id VARCHAR(64) DEFAULT NULL COMMENT '派单规则ID',
    fdispatched_at DATETIME DEFAULT NULL COMMENT '派单时间',
    fdispatcher_id VARCHAR(64) DEFAULT NULL COMMENT '派单人ID',
    fdispatcher_name VARCHAR(64) DEFAULT NULL COMMENT '派单人姓名',
    -- 执行人信息
    fassignee_id VARCHAR(64) DEFAULT NULL COMMENT '执行人ID',
    fassignee_name VARCHAR(64) DEFAULT NULL COMMENT '执行人姓名',
    fassignee_dept VARCHAR(100) DEFAULT NULL COMMENT '执行人部门',
    faccepted_at DATETIME DEFAULT NULL COMMENT '接收时间',
    fexpected_start_time DATETIME DEFAULT NULL COMMENT '预计开始时间',
    fexpected_end_time DATETIME DEFAULT NULL COMMENT '预计完成时间',
    factual_start_time DATETIME DEFAULT NULL COMMENT '实际开始时间',
    factual_end_time DATETIME DEFAULT NULL COMMENT '实际完成时间',
    -- 处理结果
    fresult_description TEXT DEFAULT NULL COMMENT '处理结果描述',
    fresult_summary VARCHAR(500) DEFAULT NULL COMMENT '处理结果摘要',
    -- 审核信息
    freviewer_id VARCHAR(64) DEFAULT NULL COMMENT '审核人ID',
    freviewer_name VARCHAR(64) DEFAULT NULL COMMENT '审核人姓名',
    freviewed_at DATETIME DEFAULT NULL COMMENT '审核时间',
    freview_opinion TEXT DEFAULT NULL COMMENT '审核意见',
    freview_result VARCHAR(20) DEFAULT NULL COMMENT '审核结果: pass=通过 reject=驳回',
    -- 评价
    fevaluation_score INT DEFAULT NULL COMMENT '评价分数(1-5)',
    fevaluation_content TEXT DEFAULT NULL COMMENT '评价内容',
    fevaluated_at DATETIME DEFAULT NULL COMMENT '评价时间',
    -- 超期
    fis_overdue INT DEFAULT 0 COMMENT '是否超期: 0=否 1=是',
    foverdue_minutes INT DEFAULT 0 COMMENT '超期分钟数',
    foverdue_type VARCHAR(20) DEFAULT NULL COMMENT '超期类型: response=响应超期 complete=完成超期',
    -- 关联
    fparent_order_id VARCHAR(64) DEFAULT NULL COMMENT '父工单ID',
    frelated_order_ids TEXT DEFAULT NULL COMMENT '关联工单IDs(JSON数组)',
    -- 附件
    fimage_urls TEXT DEFAULT NULL COMMENT '图片URLs(JSON数组)',
    fvideo_urls TEXT DEFAULT NULL COMMENT '视频URLs(JSON数组)',
    fattachment_urls TEXT DEFAULT NULL COMMENT '附件URLs(JSON数组)',
    -- 扩展
    fextra_data TEXT DEFAULT NULL COMMENT '扩展数据(JSON)',
    fremark TEXT DEFAULT NULL COMMENT '备注',
    fcreate_user_id VARCHAR(64) DEFAULT NULL COMMENT '创建人ID',
    create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    update_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    delete_time DATETIME DEFAULT NULL COMMENT '删除时间',
    is_deleted INT DEFAULT 0 COMMENT '软删除: 0=未删 1=已删',
    UNIQUE KEY uk_wo_no (fwo_no),
    INDEX idx_fec_id (fec_id),
    INDEX idx_project_id (fproject_id),
    INDEX idx_status (fstatus),
    INDEX idx_type (fwo_type),
    INDEX idx_category (fcategory_id),
    INDEX idx_priority (fpriority),
    INDEX idx_sla_level (fsla_level),
    INDEX idx_assignee (fassignee_id),
    INDEX idx_reporter (freporter_id),
    INDEX idx_template (ftemplate_id),
    INDEX idx_plan_date (fplan_date),
    INDEX idx_create_time (create_time),
    INDEX idx_parent (fparent_order_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='智慧工单主表';

-- =============================================
-- 8. 工单检查记录表 (标准周期工单的检查项结果)
-- =============================================
CREATE TABLE IF NOT EXISTS t_wo_check_record (
    fid VARCHAR(64) PRIMARY KEY COMMENT '记录ID',
    fec_id VARCHAR(64) NOT NULL COMMENT '企业ID',
    fproject_id VARCHAR(64) NOT NULL COMMENT '项目ID',
    fwo_id VARCHAR(64) NOT NULL COMMENT '工单ID',
    ftemplate_item_id VARCHAR(64) DEFAULT NULL COMMENT '模板检查项ID',
    fitem_name VARCHAR(200) NOT NULL COMMENT '检查项名称',
    fitem_type VARCHAR(20) DEFAULT 'check' COMMENT '检查项类型',
    fcheck_result VARCHAR(20) NOT NULL COMMENT '检查结果: pass=合格 fail=不合格 na=不适用',
    fscore DECIMAL(5,2) DEFAULT NULL COMMENT '评分',
    fcheck_value TEXT DEFAULT NULL COMMENT '检查值(文本/输入内容)',
    fphoto_urls TEXT DEFAULT NULL COMMENT '照片URLs(JSON数组)',
    fremark TEXT DEFAULT NULL COMMENT '备注',
    finspector_id VARCHAR(64) DEFAULT NULL COMMENT '检查人ID',
    finspector_name VARCHAR(64) DEFAULT NULL COMMENT '检查人姓名',
    fcheck_time DATETIME DEFAULT NULL COMMENT '检查时间',
    create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    update_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    delete_time DATETIME DEFAULT NULL COMMENT '删除时间',
    is_deleted INT DEFAULT 0 COMMENT '软删除: 0=未删 1=已删',
    INDEX idx_wo_id (fwo_id),
    INDEX idx_item_id (ftemplate_item_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='工单检查记录表';

-- =============================================
-- 9. 工单流转实例表 (记录每次状态变更)
-- =============================================
CREATE TABLE IF NOT EXISTS t_wo_flow_instance (
    fid VARCHAR(64) PRIMARY KEY COMMENT '实例ID',
    fec_id VARCHAR(64) NOT NULL COMMENT '企业ID',
    fproject_id VARCHAR(64) NOT NULL COMMENT '项目ID',
    fwo_id VARCHAR(64) NOT NULL COMMENT '工单ID',
    ffrom_node VARCHAR(50) DEFAULT NULL COMMENT '来源节点',
    fto_node VARCHAR(50) NOT NULL COMMENT '目标节点',
    ffrom_status VARCHAR(30) DEFAULT NULL COMMENT '来源状态',
    fto_status VARCHAR(30) NOT NULL COMMENT '目标状态',
    foperator_id VARCHAR(64) DEFAULT NULL COMMENT '操作人ID',
    foperator_name VARCHAR(64) DEFAULT NULL COMMENT '操作人姓名',
    faction VARCHAR(50) NOT NULL COMMENT '操作: create=创建 dispatch=派单 accept=接收 start=开始 execute=执行 complete=完成 submit_review=提交审核 review=审核 approve=通过 reject=驳回 close=关闭 cancel=取消 transfer=转单 escalate=升级 remind=催办',
    fopinion TEXT DEFAULT NULL COMMENT '操作意见',
    fattachment_urls TEXT DEFAULT NULL COMMENT '附件URLs(JSON数组)',
    fduration_seconds INT DEFAULT NULL COMMENT '节点停留时长(秒)',
    create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '操作时间',
    INDEX idx_wo_id (fwo_id),
    INDEX idx_operator (foperator_id),
    INDEX idx_create_time (create_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='工单流转实例表';

-- =============================================
-- 10. 工单操作日志表
-- =============================================
CREATE TABLE IF NOT EXISTS t_wo_operation_log (
    fid VARCHAR(64) PRIMARY KEY COMMENT '日志ID',
    fec_id VARCHAR(64) NOT NULL COMMENT '企业ID',
    fproject_id VARCHAR(64) NOT NULL COMMENT '项目ID',
    fwo_id VARCHAR(64) NOT NULL COMMENT '工单ID',
    foperator_id VARCHAR(64) DEFAULT NULL COMMENT '操作人ID',
    foperator_name VARCHAR(64) DEFAULT NULL COMMENT '操作人姓名',
    foperator_type VARCHAR(20) DEFAULT NULL COMMENT '操作人类型: system=系统 admin=管理员 staff=员工 owner=业主',
    faction VARCHAR(50) NOT NULL COMMENT '操作类型',
    fdetail TEXT DEFAULT NULL COMMENT '操作详情',
    fip_address VARCHAR(50) DEFAULT NULL COMMENT 'IP地址',
    fuser_agent VARCHAR(500) DEFAULT NULL COMMENT '用户代理',
    fextra_data TEXT DEFAULT NULL COMMENT '扩展数据(JSON)',
    create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '操作时间',
    INDEX idx_wo_id (fwo_id),
    INDEX idx_operator (foperator_id),
    INDEX idx_action (faction),
    INDEX idx_create_time (create_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='工单操作日志表';

-- =============================================
-- 11. 工单催办记录表
-- =============================================
CREATE TABLE IF NOT EXISTS t_wo_reminder (
    fid VARCHAR(64) PRIMARY KEY COMMENT '催办ID',
    fec_id VARCHAR(64) NOT NULL COMMENT '企业ID',
    fproject_id VARCHAR(64) NOT NULL COMMENT '项目ID',
    fwo_id VARCHAR(64) NOT NULL COMMENT '工单ID',
    freminder_type VARCHAR(20) NOT NULL COMMENT '催办类型: system=系统自动 manual=手动',
    freminder_channel VARCHAR(20) DEFAULT 'system' COMMENT '催办渠道: system=站内 push=推送 sms=短信 dingtalk=钉钉',
    freminder_content TEXT DEFAULT NULL COMMENT '催办内容',
    freminder_user_id VARCHAR(64) NOT NULL COMMENT '催办人ID',
    freminder_user_name VARCHAR(64) DEFAULT NULL COMMENT '催办人姓名',
    ftarget_user_id VARCHAR(64) NOT NULL COMMENT '被催办人ID',
    ftarget_user_name VARCHAR(64) DEFAULT NULL COMMENT '被催办人姓名',
    fis_read INT DEFAULT 0 COMMENT '是否已读: 0=未读 1=已读',
    fread_time DATETIME DEFAULT NULL COMMENT '阅读时间',
    create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    INDEX idx_wo_id (fwo_id),
    INDEX idx_target (ftarget_user_id),
    INDEX idx_create_time (create_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='工单催办记录表';

-- =============================================
-- 12. 工单统计汇总表 (定时任务更新)
-- =============================================
CREATE TABLE IF NOT EXISTS t_wo_statistics (
    fid VARCHAR(64) PRIMARY KEY COMMENT '统计ID',
    fec_id VARCHAR(64) NOT NULL COMMENT '企业ID',
    fproject_id VARCHAR(64) NOT NULL COMMENT '项目ID',
    fstat_date DATE NOT NULL COMMENT '统计日期',
    fwo_type VARCHAR(30) DEFAULT NULL COMMENT '工单类型(NULL=全部)',
    fcategory_id VARCHAR(64) DEFAULT NULL COMMENT '分类ID(NULL=全部)',
    ftotal_count INT DEFAULT 0 COMMENT '工单总数',
    fpending_count INT DEFAULT 0 COMMENT '待处理数',
    fin_progress_count INT DEFAULT 0 COMMENT '进行中数',
    fcompleted_count INT DEFAULT 0 COMMENT '已完成数',
    fclosed_count INT DEFAULT 0 COMMENT '已关闭数',
    fcancelled_count INT DEFAULT 0 COMMENT '已取消数',
    foverdue_count INT DEFAULT 0 COMMENT '超期数',
    favg_complete_minutes INT DEFAULT NULL COMMENT '平均完成时长(分钟)',
    favg_evaluation_score DECIMAL(3,2) DEFAULT NULL COMMENT '平均评价分',
    create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    update_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    UNIQUE KEY uk_date_type (fstat_date, fwo_type, fcategory_id, fproject_id, fec_id),
    INDEX idx_fec_id (fec_id),
    INDEX idx_project_id (fproject_id),
    INDEX idx_date (fstat_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='工单统计汇总表';

-- =============================================
-- 初始化数据: 默认SLA规则
-- =============================================
INSERT INTO t_wo_sla_rule (fid, fec_id, frule_name, fsla_level, fpriority, fresponse_minutes, fcomplete_hours, fescalate_minutes, fcolor, fdescription) VALUES
('sla_l1_default', 'default', '紧急-L1', 'L1', 4, 15, 2, 10, '#FF4D4F', '紧急工单: 15分钟响应, 2小时完成'),
('sla_l2_default', 'default', '高优先-L2', 'L2', 3, 30, 4, 20, '#FF7A45', '高优先工单: 30分钟响应, 4小时完成'),
('sla_l3_default', 'default', '中优先-L3', 'L3', 2, 60, 8, 45, '#FAAD14', '中优先工单: 1小时响应, 8小时完成'),
('sla_l4_default', 'default', '低优先-L4', 'L4', 1, 120, 24, 120, '#52C41A', '低优先工单: 2小时响应, 24小时完成');

-- =============================================
-- 初始化数据: 默认流转节点
-- =============================================
INSERT INTO t_wo_flow_node (fid, fec_id, fflow_name, fwo_type, fnode_code, fnode_name, fnode_type, fsort_order, fassignee_type, faction_required) VALUES
('fn_start', 'default', '标准工单流程', 'all', 'start', '开始', 'start', 1, 'creator', 0),
('fn_pending_dispatch', 'default', '标准工单流程', 'all', 'pending_dispatch', '待派单', 'task', 2, 'dispatcher', 1),
('fn_dispatched', 'default', '标准工单流程', 'all', 'dispatched', '已派单', 'task', 3, 'assignee', 1),
('fn_in_progress', 'default', '标准工单流程', 'all', 'in_progress', '执行中', 'task', 4, 'assignee', 1),
('fn_completed', 'default', '标准工单流程', 'all', 'completed', '已完成', 'task', 5, 'reviewer', 1),
('fn_closed', 'default', '标准工单流程', 'all', 'closed', '已关闭', 'end', 6, NULL, 0);

-- =============================================
-- 初始化数据: 默认工单分类
-- =============================================
INSERT INTO t_wo_category (fid, fec_id, fproject_id, fparent_id, fcategory_name, fcategory_code, fcategory_type, fsort_order) VALUES
('cat_quality', 'default', 'default_project', NULL, '品质检查', 'QUALITY', 'quality', 1),
('cat_equipment', 'default', 'default_project', NULL, '设备巡查保养', 'EQUIPMENT', 'equipment', 2),
('cat_comprehensive', 'default', 'default_project', NULL, '综合巡查', 'COMPREHENSIVE', 'comprehensive', 3),
('cat_repair', 'default', 'default_project', NULL, '报事报修', 'REPAIR', 'repair', 4),
('cat_repair_electric', 'default', 'default_project', 'cat_repair', '电气维修', 'REPAIR_ELECTRIC', 'repair', 1),
('cat_repair_plumb', 'default', 'default_project', 'cat_repair', '管道维修', 'REPAIR_PLUMB', 'repair', 2),
('cat_repair_door', 'default', 'default_project', 'cat_repair', '门窗维修', 'REPAIR_DOOR', 'repair', 3),
('cat_repair_ac', 'default', 'default_project', 'cat_repair', '空调维修', 'REPAIR_AC', 'repair', 4),
('cat_repair_other', 'default', 'default_project', 'cat_repair', '其他维修', 'REPAIR_OTHER', 'repair', 5);

-- 完成
SELECT '智慧工单系统V1.0数据库迁移完成' AS message;
