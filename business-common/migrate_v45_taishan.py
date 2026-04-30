#!/usr/bin/env python3
"""
V45.0 泰山城投需求 - 数据库迁移脚本
模块:
  1. 社区食堂管理 (cafeteria)
  2. 私宴包间管理 (banquet)
  3. 大堂饮品管理 (drink)
  4. 运动场馆管理 (sports)
  5. 洗车房管理 (carwash)
  6. 洗衣房管理 (laundry)
  7. 会员/积分/优惠券 (member/points/coupon)
  8. 社区增值服务 (community_service)
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from business_common import db


def migrate():
    """执行迁移"""
    print("开始 V45.0 泰山城投需求数据库迁移...")

    # 1. 社区食堂
    create_cafeteria_tables()

    # 2. 私宴包间
    create_banquet_tables()

    # 3. 大堂饮品
    create_drink_tables()

    # 4. 运动场馆
    create_sports_tables()

    # 5. 洗车房
    create_carwash_tables()

    # 6. 洗衣房
    create_laundry_tables()

    # 7. 会员/积分/优惠券
    create_member_tables()

    # 8. 社区增值服务
    create_community_service_tables()

    print("V45.0 泰山城投需求数据库迁移完成!")


# ============ 1. 社区食堂 ============

def create_cafeteria_tables():
    """创建社区食堂相关表"""
    print("创建社区食堂表...")

    # 菜品分类表
    db.execute("""
        CREATE TABLE IF NOT EXISTS ts_cafeteria_category (
            id INT AUTO_INCREMENT PRIMARY KEY,
            fid VARCHAR(36) NOT NULL UNIQUE,
            name VARCHAR(50) NOT NULL COMMENT '分类名称',
            icon VARCHAR(255) DEFAULT NULL COMMENT '分类图标',
            sort_order INT DEFAULT 0 COMMENT '排序',
            status TINYINT DEFAULT 1 COMMENT '1-启用 0-禁用',
            ec_id VARCHAR(36) DEFAULT NULL,
            project_id VARCHAR(36) DEFAULT NULL,
            deleted TINYINT DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            INDEX idx_ec_project (ec_id, project_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='食堂菜品分类'
    """)

    # 菜品表
    db.execute("""
        CREATE TABLE IF NOT EXISTS ts_cafeteria_dish (
            id INT AUTO_INCREMENT PRIMARY KEY,
            fid VARCHAR(36) NOT NULL UNIQUE,
            category_id INT NOT NULL COMMENT '分类ID',
            name VARCHAR(100) NOT NULL COMMENT '菜品名称',
            image VARCHAR(500) DEFAULT NULL COMMENT '菜品图片',
            price DECIMAL(10,2) NOT NULL COMMENT '价格',
            original_price DECIMAL(10,2) DEFAULT NULL COMMENT '原价',
            description TEXT COMMENT '描述',
            nutrition_tags VARCHAR(255) DEFAULT NULL COMMENT '营养标签(JSON)',
            stock INT DEFAULT 0 COMMENT '库存',
            sales INT DEFAULT 0 COMMENT '销量',
            status TINYINT DEFAULT 1 COMMENT '1-上架 0-下架',
            sort_order INT DEFAULT 0,
            ec_id VARCHAR(36) DEFAULT NULL,
            project_id VARCHAR(36) DEFAULT NULL,
            deleted TINYINT DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            INDEX idx_category (category_id),
            INDEX idx_ec_project (ec_id, project_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='食堂菜品'
    """)

    # 食堂订单表
    db.execute("""
        CREATE TABLE IF NOT EXISTS ts_cafeteria_order (
            id INT AUTO_INCREMENT PRIMARY KEY,
            fid VARCHAR(36) NOT NULL UNIQUE,
            order_no VARCHAR(32) NOT NULL UNIQUE COMMENT '订单号',
            user_id VARCHAR(64) NOT NULL,
            user_name VARCHAR(50) DEFAULT NULL,
            user_phone VARCHAR(20) DEFAULT NULL,
            order_type VARCHAR(20) NOT NULL DEFAULT 'dine_in' COMMENT 'dine_in-堂食 takeout-外卖 reserve-预定',
            table_no VARCHAR(20) DEFAULT NULL COMMENT '桌号',
            items JSON NOT NULL COMMENT '菜品列表',
            total_amount DECIMAL(10,2) NOT NULL DEFAULT 0,
            actual_amount DECIMAL(10,2) NOT NULL DEFAULT 0,
            discount_amount DECIMAL(10,2) DEFAULT 0,
            status VARCHAR(20) NOT NULL DEFAULT 'pending' COMMENT 'pending/paid/cooking/completed/cancelled',
            pay_status TINYINT DEFAULT 0 COMMENT '0-未支付 1-已支付',
            remark VARCHAR(500) DEFAULT NULL,
            pickup_time DATETIME DEFAULT NULL COMMENT '取餐时间',
            delivery_address VARCHAR(500) DEFAULT NULL COMMENT '配送地址',
            ec_id VARCHAR(36) DEFAULT NULL,
            project_id VARCHAR(36) DEFAULT NULL,
            deleted TINYINT DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            INDEX idx_user (user_id),
            INDEX idx_status (status),
            INDEX idx_ec_project (ec_id, project_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='食堂订单'
    """)


# ============ 2. 私宴包间 ============

def create_banquet_tables():
    """创建私宴包间相关表"""
    print("创建私宴包间表...")

    # 包间表
    db.execute("""
        CREATE TABLE IF NOT EXISTS ts_banquet_room (
            id INT AUTO_INCREMENT PRIMARY KEY,
            fid VARCHAR(36) NOT NULL UNIQUE,
            name VARCHAR(100) NOT NULL COMMENT '包间名称',
            image VARCHAR(500) DEFAULT NULL COMMENT '包间图片',
            images JSON DEFAULT NULL COMMENT '多张图片',
            capacity INT NOT NULL DEFAULT 10 COMMENT '容纳人数',
            price DECIMAL(10,2) NOT NULL COMMENT '基础价格',
            min_consumption DECIMAL(10,2) DEFAULT 0 COMMENT '最低消费',
            facilities VARCHAR(500) DEFAULT NULL COMMENT '设施描述',
            description TEXT COMMENT '描述',
            status TINYINT DEFAULT 1 COMMENT '1-可用 0-维护中',
            sort_order INT DEFAULT 0,
            ec_id VARCHAR(36) DEFAULT NULL,
            project_id VARCHAR(36) DEFAULT NULL,
            deleted TINYINT DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            INDEX idx_ec_project (ec_id, project_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='私宴包间'
    """)

    # 包间预约表
    db.execute("""
        CREATE TABLE IF NOT EXISTS ts_banquet_booking (
            id INT AUTO_INCREMENT PRIMARY KEY,
            fid VARCHAR(36) NOT NULL UNIQUE,
            booking_no VARCHAR(32) NOT NULL UNIQUE COMMENT '预约号',
            room_id INT NOT NULL COMMENT '包间ID',
            room_name VARCHAR(100) DEFAULT NULL,
            user_id VARCHAR(64) NOT NULL,
            user_name VARCHAR(50) DEFAULT NULL,
            user_phone VARCHAR(20) DEFAULT NULL,
            booking_date DATE NOT NULL COMMENT '预约日期',
            start_time VARCHAR(10) NOT NULL COMMENT '开始时间 HH:MM',
            end_time VARCHAR(10) NOT NULL COMMENT '结束时间 HH:MM',
            guest_count INT DEFAULT 0 COMMENT '用餐人数',
            custom_request TEXT COMMENT '定制需求',
            total_amount DECIMAL(10,2) DEFAULT 0,
            status VARCHAR(20) NOT NULL DEFAULT 'pending' COMMENT 'pending/confirmed/completed/cancelled/rejected',
            remark VARCHAR(500) DEFAULT NULL,
            ec_id VARCHAR(36) DEFAULT NULL,
            project_id VARCHAR(36) DEFAULT NULL,
            deleted TINYINT DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            INDEX idx_user (user_id),
            INDEX idx_room_date (room_id, booking_date),
            INDEX idx_status (status)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='包间预约'
    """)


# ============ 3. 大堂饮品 ============

def create_drink_tables():
    """创建大堂饮品相关表"""
    print("创建大堂饮品表...")

    # 饮品分类表
    db.execute("""
        CREATE TABLE IF NOT EXISTS ts_drink_category (
            id INT AUTO_INCREMENT PRIMARY KEY,
            fid VARCHAR(36) NOT NULL UNIQUE,
            name VARCHAR(50) NOT NULL COMMENT '分类名称',
            icon VARCHAR(255) DEFAULT NULL,
            sort_order INT DEFAULT 0,
            status TINYINT DEFAULT 1,
            ec_id VARCHAR(36) DEFAULT NULL,
            project_id VARCHAR(36) DEFAULT NULL,
            deleted TINYINT DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            INDEX idx_ec_project (ec_id, project_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='饮品分类'
    """)

    # 饮品表
    db.execute("""
        CREATE TABLE IF NOT EXISTS ts_drink_item (
            id INT AUTO_INCREMENT PRIMARY KEY,
            fid VARCHAR(36) NOT NULL UNIQUE,
            category_id INT NOT NULL COMMENT '分类ID',
            name VARCHAR(100) NOT NULL COMMENT '饮品名称',
            image VARCHAR(500) DEFAULT NULL,
            price DECIMAL(10,2) NOT NULL,
            original_price DECIMAL(10,2) DEFAULT NULL,
            description TEXT,
            specs JSON DEFAULT NULL COMMENT '规格选项(大杯/中杯/小杯)',
            stock INT DEFAULT 0,
            sales INT DEFAULT 0,
            status TINYINT DEFAULT 1 COMMENT '1-上架 0-下架',
            sort_order INT DEFAULT 0,
            ec_id VARCHAR(36) DEFAULT NULL,
            project_id VARCHAR(36) DEFAULT NULL,
            deleted TINYINT DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            INDEX idx_category (category_id),
            INDEX idx_ec_project (ec_id, project_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='饮品'
    """)

    # 饮品订单表
    db.execute("""
        CREATE TABLE IF NOT EXISTS ts_drink_order (
            id INT AUTO_INCREMENT PRIMARY KEY,
            fid VARCHAR(36) NOT NULL UNIQUE,
            order_no VARCHAR(32) NOT NULL UNIQUE,
            user_id VARCHAR(64) NOT NULL,
            user_name VARCHAR(50) DEFAULT NULL,
            user_phone VARCHAR(20) DEFAULT NULL,
            items JSON NOT NULL COMMENT '饮品列表',
            total_amount DECIMAL(10,2) NOT NULL DEFAULT 0,
            actual_amount DECIMAL(10,2) NOT NULL DEFAULT 0,
            status VARCHAR(20) NOT NULL DEFAULT 'pending' COMMENT 'pending/paid/making/delivering/completed/cancelled',
            pay_status TINYINT DEFAULT 0,
            delivery_type VARCHAR(20) DEFAULT 'self' COMMENT 'self-自取 delivery-配送',
            delivery_address VARCHAR(500) DEFAULT NULL,
            remark VARCHAR(500) DEFAULT NULL,
            ec_id VARCHAR(36) DEFAULT NULL,
            project_id VARCHAR(36) DEFAULT NULL,
            deleted TINYINT DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            INDEX idx_user (user_id),
            INDEX idx_status (status)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='饮品订单'
    """)


# ============ 4. 运动场馆 ============

def create_sports_tables():
    """创建运动场馆相关表"""
    print("创建运动场馆表...")

    # 场馆表
    db.execute("""
        CREATE TABLE IF NOT EXISTS ts_sports_venue (
            id INT AUTO_INCREMENT PRIMARY KEY,
            fid VARCHAR(36) NOT NULL UNIQUE,
            name VARCHAR(100) NOT NULL COMMENT '场馆名称',
            type VARCHAR(50) NOT NULL COMMENT '场馆类型(badminton/basketball/tennis/gym/swimming/yoga)',
            image VARCHAR(500) DEFAULT NULL,
            images JSON DEFAULT NULL,
            capacity INT DEFAULT 1 COMMENT '容纳人数/场地数',
            price_per_hour DECIMAL(10,2) NOT NULL COMMENT '每小时价格',
            description TEXT,
            facilities VARCHAR(500) DEFAULT NULL COMMENT '设施说明',
            open_time VARCHAR(10) DEFAULT '08:00' COMMENT '开放时间',
            close_time VARCHAR(20) DEFAULT '22:00' COMMENT '关闭时间',
            status TINYINT DEFAULT 1 COMMENT '1-开放 0-关闭 2-维护',
            sort_order INT DEFAULT 0,
            ec_id VARCHAR(36) DEFAULT NULL,
            project_id VARCHAR(36) DEFAULT NULL,
            deleted TINYINT DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            INDEX idx_type (type),
            INDEX idx_ec_project (ec_id, project_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='运动场馆'
    """)

    # 场馆预约表
    db.execute("""
        CREATE TABLE IF NOT EXISTS ts_sports_booking (
            id INT AUTO_INCREMENT PRIMARY KEY,
            fid VARCHAR(36) NOT NULL UNIQUE,
            booking_no VARCHAR(32) NOT NULL UNIQUE,
            venue_id INT NOT NULL,
            venue_name VARCHAR(100) DEFAULT NULL,
            user_id VARCHAR(64) NOT NULL,
            user_name VARCHAR(50) DEFAULT NULL,
            user_phone VARCHAR(20) DEFAULT NULL,
            booking_date DATE NOT NULL,
            start_time VARCHAR(10) NOT NULL,
            end_time VARCHAR(10) NOT NULL,
            duration_hours DECIMAL(4,1) DEFAULT 1,
            total_amount DECIMAL(10,2) NOT NULL DEFAULT 0,
            status VARCHAR(20) NOT NULL DEFAULT 'pending' COMMENT 'pending/confirmed/using/completed/cancelled',
            pay_status TINYINT DEFAULT 0,
            qr_code VARCHAR(255) DEFAULT NULL COMMENT '核销二维码',
            check_in_time DATETIME DEFAULT NULL,
            remark VARCHAR(500) DEFAULT NULL,
            ec_id VARCHAR(36) DEFAULT NULL,
            project_id VARCHAR(36) DEFAULT NULL,
            deleted TINYINT DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            INDEX idx_user (user_id),
            INDEX idx_venue_date (venue_id, booking_date),
            INDEX idx_status (status)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='场馆预约'
    """)


# ============ 5. 洗车房 ============

def create_carwash_tables():
    """创建洗车房相关表"""
    print("创建洗车房表...")

    # 洗车服务项目表
    db.execute("""
        CREATE TABLE IF NOT EXISTS ts_carwash_service (
            id INT AUTO_INCREMENT PRIMARY KEY,
            fid VARCHAR(36) NOT NULL UNIQUE,
            name VARCHAR(100) NOT NULL COMMENT '服务名称',
            image VARCHAR(500) DEFAULT NULL,
            price DECIMAL(10,2) NOT NULL,
            original_price DECIMAL(10,2) DEFAULT NULL,
            description TEXT,
            duration_minutes INT DEFAULT 30 COMMENT '预计时长(分钟)',
            status TINYINT DEFAULT 1,
            sort_order INT DEFAULT 0,
            ec_id VARCHAR(36) DEFAULT NULL,
            project_id VARCHAR(36) DEFAULT NULL,
            deleted TINYINT DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            INDEX idx_ec_project (ec_id, project_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='洗车服务项目'
    """)

    # 洗车工位表
    db.execute("""
        CREATE TABLE IF NOT EXISTS ts_carwash_station (
            id INT AUTO_INCREMENT PRIMARY KEY,
            fid VARCHAR(36) NOT NULL UNIQUE,
            name VARCHAR(50) NOT NULL COMMENT '工位名称',
            status TINYINT DEFAULT 1 COMMENT '1-空闲 0-维护 2-使用中',
            ec_id VARCHAR(36) DEFAULT NULL,
            project_id VARCHAR(36) DEFAULT NULL,
            deleted TINYINT DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='洗车工位'
    """)

    # 洗车订单表
    db.execute("""
        CREATE TABLE IF NOT EXISTS ts_carwash_order (
            id INT AUTO_INCREMENT PRIMARY KEY,
            fid VARCHAR(36) NOT NULL UNIQUE,
            order_no VARCHAR(32) NOT NULL UNIQUE,
            user_id VARCHAR(64) NOT NULL,
            user_name VARCHAR(50) DEFAULT NULL,
            user_phone VARCHAR(20) DEFAULT NULL,
            car_no VARCHAR(20) DEFAULT NULL COMMENT '车牌号',
            service_id INT DEFAULT NULL COMMENT '服务项目ID',
            service_name VARCHAR(100) DEFAULT NULL,
            station_id INT DEFAULT NULL COMMENT '工位ID',
            station_name VARCHAR(50) DEFAULT NULL,
            booking_time DATETIME DEFAULT NULL COMMENT '预约时间',
            total_amount DECIMAL(10,2) NOT NULL DEFAULT 0,
            status VARCHAR(20) NOT NULL DEFAULT 'pending' COMMENT 'pending/paid/washing/completed/cancelled',
            pay_status TINYINT DEFAULT 0,
            qr_code VARCHAR(255) DEFAULT NULL,
            remark VARCHAR(500) DEFAULT NULL,
            ec_id VARCHAR(36) DEFAULT NULL,
            project_id VARCHAR(36) DEFAULT NULL,
            deleted TINYINT DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            INDEX idx_user (user_id),
            INDEX idx_status (status)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='洗车订单'
    """)


# ============ 6. 洗衣房 ============

def create_laundry_tables():
    """创建洗衣房相关表"""
    print("创建洗衣房表...")

    # 洗衣服务项目表
    db.execute("""
        CREATE TABLE IF NOT EXISTS ts_laundry_service (
            id INT AUTO_INCREMENT PRIMARY KEY,
            fid VARCHAR(36) NOT NULL UNIQUE,
            name VARCHAR(100) NOT NULL COMMENT '服务名称(干洗/水洗/熨烫等)',
            image VARCHAR(500) DEFAULT NULL,
            price DECIMAL(10,2) NOT NULL COMMENT '单价(按件)',
            description TEXT,
            status TINYINT DEFAULT 1,
            sort_order INT DEFAULT 0,
            ec_id VARCHAR(36) DEFAULT NULL,
            project_id VARCHAR(36) DEFAULT NULL,
            deleted TINYINT DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            INDEX idx_ec_project (ec_id, project_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='洗衣服务项目'
    """)

    # 洗衣物价表(按衣物类型)
    db.execute("""
        CREATE TABLE IF NOT EXISTS ts_laundry_price (
            id INT AUTO_INCREMENT PRIMARY KEY,
            fid VARCHAR(36) NOT NULL UNIQUE,
            clothing_type VARCHAR(50) NOT NULL COMMENT '衣物类型(衬衫/外套/裤子/西装/大衣等)',
            service_id INT NOT NULL COMMENT '服务项目ID',
            price DECIMAL(10,2) NOT NULL,
            sort_order INT DEFAULT 0,
            ec_id VARCHAR(36) DEFAULT NULL,
            project_id VARCHAR(36) DEFAULT NULL,
            deleted TINYINT DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            INDEX idx_service (service_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='洗衣物价表'
    """)

    # 洗衣订单表
    db.execute("""
        CREATE TABLE IF NOT EXISTS ts_laundry_order (
            id INT AUTO_INCREMENT PRIMARY KEY,
            fid VARCHAR(36) NOT NULL UNIQUE,
            order_no VARCHAR(32) NOT NULL UNIQUE,
            user_id VARCHAR(64) NOT NULL,
            user_name VARCHAR(50) DEFAULT NULL,
            user_phone VARCHAR(20) DEFAULT NULL,
            items JSON NOT NULL COMMENT '衣物列表',
            total_count INT DEFAULT 0 COMMENT '衣物总件数',
            total_amount DECIMAL(10,2) NOT NULL DEFAULT 0,
            actual_amount DECIMAL(10,2) NOT NULL DEFAULT 0,
            status VARCHAR(20) NOT NULL DEFAULT 'pending' COMMENT 'pending/paid/washing/delivered/completed/cancelled',
            pay_status TINYINT DEFAULT 0,
            pickup_type VARCHAR(20) DEFAULT 'self' COMMENT 'self-自送 pickup-上门取件',
            pickup_address VARCHAR(500) DEFAULT NULL,
            pickup_time DATETIME DEFAULT NULL,
            delivery_time DATETIME DEFAULT NULL,
            qr_code VARCHAR(255) DEFAULT NULL,
            remark VARCHAR(500) DEFAULT NULL,
            ec_id VARCHAR(36) DEFAULT NULL,
            project_id VARCHAR(36) DEFAULT NULL,
            deleted TINYINT DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            INDEX idx_user (user_id),
            INDEX idx_status (status)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='洗衣订单'
    """)


# ============ 7. 会员/积分/优惠券 ============

def create_member_tables():
    """创建会员/积分/优惠券相关表"""
    print("创建会员/积分/优惠券表...")

    # 会员等级表
    db.execute("""
        CREATE TABLE IF NOT EXISTS ts_member_level (
            id INT AUTO_INCREMENT PRIMARY KEY,
            fid VARCHAR(36) NOT NULL UNIQUE,
            name VARCHAR(50) NOT NULL COMMENT '等级名称',
            level INT NOT NULL DEFAULT 1 COMMENT '等级序号',
            min_points INT DEFAULT 0 COMMENT '最低积分',
            discount_rate DECIMAL(3,2) DEFAULT 1.00 COMMENT '折扣率',
            icon VARCHAR(255) DEFAULT NULL,
            benefits TEXT COMMENT '权益描述',
            status TINYINT DEFAULT 1,
            ec_id VARCHAR(36) DEFAULT NULL,
            project_id VARCHAR(36) DEFAULT NULL,
            deleted TINYINT DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            UNIQUE KEY uk_level (level, ec_id, project_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='会员等级'
    """)

    # 会员信息表
    db.execute("""
        CREATE TABLE IF NOT EXISTS ts_member (
            id INT AUTO_INCREMENT PRIMARY KEY,
            fid VARCHAR(36) NOT NULL UNIQUE,
            user_id VARCHAR(64) NOT NULL COMMENT '关联用户ID',
            user_name VARCHAR(50) DEFAULT NULL,
            user_phone VARCHAR(20) DEFAULT NULL,
            level_id INT DEFAULT NULL COMMENT '会员等级ID',
            level_name VARCHAR(50) DEFAULT NULL,
            points INT DEFAULT 0 COMMENT '当前积分',
            total_points INT DEFAULT 0 COMMENT '累计积分',
            total_consumption DECIMAL(12,2) DEFAULT 0 COMMENT '累计消费',
            balance DECIMAL(10,2) DEFAULT 0 COMMENT '储值余额',
            card_no VARCHAR(32) DEFAULT NULL COMMENT '会员卡号',
            status TINYINT DEFAULT 1 COMMENT '1-正常 0-冻结',
            ec_id VARCHAR(36) DEFAULT NULL,
            project_id VARCHAR(36) DEFAULT NULL,
            deleted TINYINT DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            UNIQUE KEY uk_user (user_id, ec_id, project_id),
            INDEX idx_card (card_no)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='会员信息'
    """)

    # 积分流水表
    db.execute("""
        CREATE TABLE IF NOT EXISTS ts_points_log (
            id INT AUTO_INCREMENT PRIMARY KEY,
            fid VARCHAR(36) NOT NULL UNIQUE,
            member_id INT NOT NULL COMMENT '会员ID',
            user_id VARCHAR(64) NOT NULL,
            type VARCHAR(20) NOT NULL COMMENT 'earn-获取 spend-消费 expire-过期 refund-退还',
            points INT NOT NULL COMMENT '积分数量(正数)',
            balance INT DEFAULT 0 COMMENT '变动后余额',
            source VARCHAR(50) DEFAULT NULL COMMENT '来源(order/checkin/activity/manual)',
            source_id VARCHAR(64) DEFAULT NULL COMMENT '来源ID',
            description VARCHAR(200) DEFAULT NULL,
            ec_id VARCHAR(36) DEFAULT NULL,
            project_id VARCHAR(36) DEFAULT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_member (member_id),
            INDEX idx_user (user_id),
            INDEX idx_type (type)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='积分流水'
    """)

    # 优惠券模板表
    db.execute("""
        CREATE TABLE IF NOT EXISTS ts_coupon_template (
            id INT AUTO_INCREMENT PRIMARY KEY,
            fid VARCHAR(36) NOT NULL UNIQUE,
            name VARCHAR(100) NOT NULL COMMENT '优惠券名称',
            type VARCHAR(20) NOT NULL COMMENT 'fixed-满减 discount-折扣 cash-代金券',
            value DECIMAL(10,2) NOT NULL COMMENT '面值/折扣率',
            min_amount DECIMAL(10,2) DEFAULT 0 COMMENT '最低消费金额',
            total_count INT DEFAULT 0 COMMENT '发放总量(0-不限)',
            issued_count INT DEFAULT 0 COMMENT '已发放数',
            used_count INT DEFAULT 0 COMMENT '已使用数',
            applicable_scope VARCHAR(20) DEFAULT 'all' COMMENT 'all-全场 specific-指定品类',
            scope_ids JSON DEFAULT NULL COMMENT '适用品类/商品ID列表',
            start_time DATETIME DEFAULT NULL COMMENT '有效期开始',
            end_time DATETIME DEFAULT NULL COMMENT '有效期结束',
            status TINYINT DEFAULT 1 COMMENT '1-启用 0-禁用',
            ec_id VARCHAR(36) DEFAULT NULL,
            project_id VARCHAR(36) DEFAULT NULL,
            deleted TINYINT DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            INDEX idx_status (status),
            INDEX idx_time (start_time, end_time)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='优惠券模板'
    """)

    # 用户优惠券表
    db.execute("""
        CREATE TABLE IF NOT EXISTS ts_user_coupon (
            id INT AUTO_INCREMENT PRIMARY KEY,
            fid VARCHAR(36) NOT NULL UNIQUE,
            template_id INT NOT NULL COMMENT '模板ID',
            coupon_name VARCHAR(100) DEFAULT NULL,
            coupon_type VARCHAR(20) DEFAULT NULL,
            coupon_value DECIMAL(10,2) DEFAULT NULL,
            min_amount DECIMAL(10,2) DEFAULT 0,
            user_id VARCHAR(64) NOT NULL,
            status TINYINT DEFAULT 0 COMMENT '0-未使用 1-已使用 2-已过期',
            used_order_id VARCHAR(64) DEFAULT NULL,
            used_time DATETIME DEFAULT NULL,
            expire_time DATETIME DEFAULT NULL,
            ec_id VARCHAR(36) DEFAULT NULL,
            project_id VARCHAR(36) DEFAULT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_user_status (user_id, status),
            INDEX idx_expire (expire_time)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户优惠券'
    """)

    # 消费总账表
    db.execute("""
        CREATE TABLE IF NOT EXISTS ts_consumption_ledger (
            id INT AUTO_INCREMENT PRIMARY KEY,
            fid VARCHAR(36) NOT NULL UNIQUE,
            user_id VARCHAR(64) NOT NULL,
            user_name VARCHAR(50) DEFAULT NULL,
            module VARCHAR(30) NOT NULL COMMENT '模块(cafeteria/banquet/drink/sports/carwash/laundry)',
            order_id INT DEFAULT NULL COMMENT '关联订单ID',
            order_no VARCHAR(32) DEFAULT NULL,
            amount DECIMAL(10,2) NOT NULL COMMENT '消费金额',
            points_earned INT DEFAULT 0 COMMENT '获得积分',
            points_used INT DEFAULT 0 COMMENT '使用积分',
            coupon_id INT DEFAULT NULL COMMENT '使用优惠券ID',
            discount_amount DECIMAL(10,2) DEFAULT 0 COMMENT '优惠金额',
            pay_amount DECIMAL(10,2) NOT NULL COMMENT '实付金额',
            ec_id VARCHAR(36) DEFAULT NULL,
            project_id VARCHAR(36) DEFAULT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_user (user_id),
            INDEX idx_module (module),
            INDEX idx_date (created_at)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='消费总账'
    """)


# ============ 8. 社区增值服务 ============

def create_community_service_tables():
    """创建社区增值服务相关表"""
    print("创建社区增值服务表...")

    # 服务分类表
    db.execute("""
        CREATE TABLE IF NOT EXISTS ts_community_category (
            id INT AUTO_INCREMENT PRIMARY KEY,
            fid VARCHAR(36) NOT NULL UNIQUE,
            name VARCHAR(50) NOT NULL COMMENT '分类名称(家政/快递/邻里/便民)',
            icon VARCHAR(255) DEFAULT NULL,
            sort_order INT DEFAULT 0,
            status TINYINT DEFAULT 1,
            ec_id VARCHAR(36) DEFAULT NULL,
            project_id VARCHAR(36) DEFAULT NULL,
            deleted TINYINT DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='社区服务分类'
    """)

    # 服务项目表
    db.execute("""
        CREATE TABLE IF NOT EXISTS ts_community_service (
            id INT AUTO_INCREMENT PRIMARY KEY,
            fid VARCHAR(36) NOT NULL UNIQUE,
            category_id INT NOT NULL COMMENT '分类ID',
            name VARCHAR(100) NOT NULL COMMENT '服务名称',
            image VARCHAR(500) DEFAULT NULL,
            price DECIMAL(10,2) DEFAULT 0 COMMENT '价格(0-面议)',
            price_unit VARCHAR(20) DEFAULT NULL COMMENT '价格单位(次/小时/件)',
            description TEXT,
            contact_phone VARCHAR(20) DEFAULT NULL,
            contact_name VARCHAR(50) DEFAULT NULL,
            status TINYINT DEFAULT 1,
            sort_order INT DEFAULT 0,
            ec_id VARCHAR(36) DEFAULT NULL,
            project_id VARCHAR(36) DEFAULT NULL,
            deleted TINYINT DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            INDEX idx_category (category_id),
            INDEX idx_ec_project (ec_id, project_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='社区服务项目'
    """)

    # 社区活动表
    db.execute("""
        CREATE TABLE IF NOT EXISTS ts_community_activity (
            id INT AUTO_INCREMENT PRIMARY KEY,
            fid VARCHAR(36) NOT NULL UNIQUE,
            title VARCHAR(200) NOT NULL COMMENT '活动标题',
            cover VARCHAR(500) DEFAULT NULL COMMENT '封面图',
            content TEXT COMMENT '活动详情',
            activity_type VARCHAR(30) DEFAULT 'event' COMMENT 'event-活动 volunteer-志愿 market-集市',
            start_time DATETIME NOT NULL,
            end_time DATETIME NOT NULL,
            location VARCHAR(200) DEFAULT NULL COMMENT '活动地点',
            max_participants INT DEFAULT 0 COMMENT '最大参与人数(0-不限)',
            current_participants INT DEFAULT 0,
            status TINYINT DEFAULT 1 COMMENT '1-报名中 2-进行中 3-已结束 0-已取消',
            ec_id VARCHAR(36) DEFAULT NULL,
            project_id VARCHAR(36) DEFAULT NULL,
            deleted TINYINT DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            INDEX idx_status (status),
            INDEX idx_time (start_time, end_time)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='社区活动'
    """)

    # 活动报名表
    db.execute("""
        CREATE TABLE IF NOT EXISTS ts_community_activity_signup (
            id INT AUTO_INCREMENT PRIMARY KEY,
            fid VARCHAR(36) NOT NULL UNIQUE,
            activity_id INT NOT NULL,
            user_id VARCHAR(64) NOT NULL,
            user_name VARCHAR(50) DEFAULT NULL,
            user_phone VARCHAR(20) DEFAULT NULL,
            participant_count INT DEFAULT 1,
            status TINYINT DEFAULT 1 COMMENT '1-已报名 2-已签到 0-已取消',
            ec_id VARCHAR(36) DEFAULT NULL,
            project_id VARCHAR(36) DEFAULT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            UNIQUE KEY uk_activity_user (activity_id, user_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='活动报名'
    """)

    # 二手闲置/邻里互助帖子表
    db.execute("""
        CREATE TABLE IF NOT EXISTS ts_community_post (
            id INT AUTO_INCREMENT PRIMARY KEY,
            fid VARCHAR(36) NOT NULL UNIQUE,
            user_id VARCHAR(64) NOT NULL,
            user_name VARCHAR(50) DEFAULT NULL,
            user_avatar VARCHAR(500) DEFAULT NULL,
            type VARCHAR(20) NOT NULL COMMENT 'idle-闲置 help-互助 info-资讯',
            title VARCHAR(200) NOT NULL,
            content TEXT,
            images JSON DEFAULT NULL,
            price DECIMAL(10,2) DEFAULT NULL COMMENT '闲置价格',
            contact_info VARCHAR(100) DEFAULT NULL,
            view_count INT DEFAULT 0,
            like_count INT DEFAULT 0,
            comment_count INT DEFAULT 0,
            status TINYINT DEFAULT 1 COMMENT '1-正常 0-下架',
            ec_id VARCHAR(36) DEFAULT NULL,
            project_id VARCHAR(36) DEFAULT NULL,
            deleted TINYINT DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            INDEX idx_user (user_id),
            INDEX idx_type (type),
            INDEX idx_ec_project (ec_id, project_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='社区帖子'
    """)


if __name__ == '__main__':
    migrate()
