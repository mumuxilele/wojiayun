#!/usr/bin/env python3
import pymysql

conn = pymysql.connect(
    host='localhost', port=3306, user='root',
    password='Wojiacloud$2023', database='visit_system', charset='utf8mb4'
)

tables_sql = {
    'business_member_levels': '''CREATE TABLE IF NOT EXISTS business_member_levels (
        id INT AUTO_INCREMENT PRIMARY KEY,
        name VARCHAR(100) NOT NULL,
        code VARCHAR(50) DEFAULT NULL,
        level INT DEFAULT 0,
        min_points INT DEFAULT 0,
        max_points INT DEFAULT 0,
        discount DECIMAL(5,2) DEFAULT 1.00,
        points_rate DECIMAL(5,2) DEFAULT 1.00,
        icon VARCHAR(200) DEFAULT NULL,
        description TEXT,
        benefits TEXT,
        is_active TINYINT DEFAULT 1,
        sort_order INT DEFAULT 0,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4''',

    'business_points_exchanges': '''CREATE TABLE IF NOT EXISTS business_points_exchanges (
        id INT AUTO_INCREMENT PRIMARY KEY,
        user_id INT NOT NULL,
        goods_id INT DEFAULT NULL,
        goods_name VARCHAR(200) DEFAULT '',
        points_cost INT DEFAULT 0,
        status VARCHAR(20) DEFAULT 'pending',
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4''',

    'business_user_achievements': '''CREATE TABLE IF NOT EXISTS business_user_achievements (
        id INT AUTO_INCREMENT PRIMARY KEY,
        user_id INT NOT NULL,
        achievement_id INT DEFAULT NULL,
        achievement_name VARCHAR(200) DEFAULT '',
        status VARCHAR(20) DEFAULT 'locked',
        unlocked_at DATETIME DEFAULT NULL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4''',

    'business_achievements': '''CREATE TABLE IF NOT EXISTS business_achievements (
        id INT AUTO_INCREMENT PRIMARY KEY,
        name VARCHAR(100) NOT NULL,
        code VARCHAR(50) DEFAULT NULL,
        icon VARCHAR(200) DEFAULT NULL,
        description TEXT,
        condition_type VARCHAR(50) DEFAULT NULL,
        condition_value INT DEFAULT 0,
        reward_points INT DEFAULT 0,
        is_active TINYINT DEFAULT 1,
        sort_order INT DEFAULT 0,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4''',

    'business_cart': '''CREATE TABLE IF NOT EXISTS business_cart (
        id INT AUTO_INCREMENT PRIMARY KEY,
        user_id INT NOT NULL,
        product_id INT NOT NULL,
        sku_id INT DEFAULT NULL,
        quantity INT DEFAULT 1,
        spec_info VARCHAR(500) DEFAULT '',
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4''',

    'business_seckill_orders': '''CREATE TABLE IF NOT EXISTS business_seckill_orders (
        id INT AUTO_INCREMENT PRIMARY KEY,
        user_id INT NOT NULL,
        product_id INT DEFAULT NULL,
        order_no VARCHAR(64) DEFAULT NULL,
        status VARCHAR(20) DEFAULT 'pending',
        total_amount DECIMAL(10,2) DEFAULT 0,
        paid_amount DECIMAL(10,2) DEFAULT 0,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4''',

    'business_promotion_users': '''CREATE TABLE IF NOT EXISTS business_promotion_users (
        id INT AUTO_INCREMENT PRIMARY KEY,
        promotion_id INT NOT NULL,
        user_id INT NOT NULL,
        status VARCHAR(20) DEFAULT 'active',
        joined_at DATETIME DEFAULT CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4''',

    'business_feedback': '''CREATE TABLE IF NOT EXISTS business_feedback (
        id INT AUTO_INCREMENT PRIMARY KEY,
        user_id INT NOT NULL,
        type VARCHAR(50) DEFAULT 'suggestion',
        content TEXT,
        contact VARCHAR(200) DEFAULT '',
        images TEXT,
        status VARCHAR(20) DEFAULT 'pending',
        reply TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        replied_at DATETIME DEFAULT NULL
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4''',

    'business_user_addresses': '''CREATE TABLE IF NOT EXISTS business_user_addresses (
        id INT AUTO_INCREMENT PRIMARY KEY,
        user_id INT NOT NULL,
        contact_name VARCHAR(100) DEFAULT '',
        contact_phone VARCHAR(20) DEFAULT '',
        province VARCHAR(50) DEFAULT '',
        city VARCHAR(50) DEFAULT '',
        district VARCHAR(50) DEFAULT '',
        detail_address VARCHAR(500) DEFAULT '',
        is_default TINYINT DEFAULT 0,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4''',

    'business_checkin_logs': '''CREATE TABLE IF NOT EXISTS business_checkin_logs (
        id INT AUTO_INCREMENT PRIMARY KEY,
        user_id INT NOT NULL,
        points_earned INT DEFAULT 0,
        checkin_date DATE NOT NULL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4''',

    'business_search_history': '''CREATE TABLE IF NOT EXISTS business_search_history (
        id INT AUTO_INCREMENT PRIMARY KEY,
        user_id INT NOT NULL,
        keyword VARCHAR(200) DEFAULT '',
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4''',

    'business_recently_viewed': '''CREATE TABLE IF NOT EXISTS business_recently_viewed (
        id INT AUTO_INCREMENT PRIMARY KEY,
        user_id INT NOT NULL,
        product_id INT NOT NULL,
        viewed_at DATETIME DEFAULT CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4''',

    'business_favorites': '''CREATE TABLE IF NOT EXISTS business_favorites (
        id INT AUTO_INCREMENT PRIMARY KEY,
        user_id VARCHAR(64) NOT NULL COMMENT '用户ID',
        target_id INT NOT NULL COMMENT '收藏对象ID',
        target_type VARCHAR(50) DEFAULT 'product' COMMENT '收藏对象类型',
        target_name VARCHAR(200) DEFAULT '' COMMENT '收藏对象名称（冗余）',
        ec_id VARCHAR(64) DEFAULT NULL COMMENT '企业ID',
        project_id VARCHAR(64) DEFAULT NULL COMMENT '项目ID',
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4''',

    'business_points_log': '''CREATE TABLE IF NOT EXISTS business_points_log (
        id INT AUTO_INCREMENT PRIMARY KEY,
        user_id INT NOT NULL,
        points INT DEFAULT 0,
        type VARCHAR(50) DEFAULT 'earn',
        source VARCHAR(100) DEFAULT '',
        description VARCHAR(500) DEFAULT '',
        related_id INT DEFAULT NULL,
        related_type VARCHAR(50) DEFAULT NULL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4''',

    'business_notices': '''CREATE TABLE IF NOT EXISTS business_notices (
        id INT AUTO_INCREMENT PRIMARY KEY,
        title VARCHAR(200) NOT NULL DEFAULT '',
        content TEXT,
        type VARCHAR(50) DEFAULT 'notice',
        is_published TINYINT DEFAULT 0,
        published_at DATETIME DEFAULT NULL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4''',

    'business_invoice_titles': '''CREATE TABLE IF NOT EXISTS business_invoice_titles (
        id INT AUTO_INCREMENT PRIMARY KEY,
        user_id INT NOT NULL,
        title VARCHAR(200) DEFAULT '',
        tax_no VARCHAR(50) DEFAULT '',
        type VARCHAR(20) DEFAULT 'personal',
        is_default TINYINT DEFAULT 0,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4''',

    'business_invoices': '''CREATE TABLE IF NOT EXISTS business_invoices (
        id INT AUTO_INCREMENT PRIMARY KEY,
        user_id INT NOT NULL,
        order_id INT DEFAULT NULL,
        invoice_title VARCHAR(200) DEFAULT '',
        tax_no VARCHAR(50) DEFAULT '',
        amount DECIMAL(10,2) DEFAULT 0,
        status VARCHAR(20) DEFAULT 'pending',
        invoice_url VARCHAR(500) DEFAULT '',
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4''',

    'business_reviews': '''CREATE TABLE IF NOT EXISTS business_reviews (
        id INT AUTO_INCREMENT PRIMARY KEY,
        user_id INT NOT NULL,
        order_id INT DEFAULT NULL,
        product_id INT DEFAULT NULL,
        rating INT DEFAULT 5,
        content TEXT,
        images TEXT,
        is_anonymous TINYINT DEFAULT 0,
        reply TEXT,
        status VARCHAR(20) DEFAULT 'published',
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        replied_at DATETIME DEFAULT NULL
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4''',

    'business_user_coupons': '''CREATE TABLE IF NOT EXISTS business_user_coupons (
        id INT AUTO_INCREMENT PRIMARY KEY,
        user_id INT NOT NULL,
        coupon_id INT NOT NULL,
        status VARCHAR(20) DEFAULT 'unused',
        used_order_id INT DEFAULT NULL,
        received_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        used_at DATETIME DEFAULT NULL,
        expired_at DATETIME DEFAULT NULL
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4''',

    'business_coupons': '''CREATE TABLE IF NOT EXISTS business_coupons (
        id INT AUTO_INCREMENT PRIMARY KEY,
        name VARCHAR(200) NOT NULL,
        type VARCHAR(20) DEFAULT 'fixed',
        value DECIMAL(10,2) DEFAULT 0,
        min_amount DECIMAL(10,2) DEFAULT 0,
        total_count INT DEFAULT 0,
        used_count INT DEFAULT 0,
        start_time DATETIME DEFAULT NULL,
        end_time DATETIME DEFAULT NULL,
        status VARCHAR(20) DEFAULT 'active',
        description TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4''',

    'business_shops': '''CREATE TABLE IF NOT EXISTS business_shops (
        id INT AUTO_INCREMENT PRIMARY KEY,
        name VARCHAR(200) NOT NULL,
        description TEXT,
        address VARCHAR(500) DEFAULT '',
        phone VARCHAR(20) DEFAULT '',
        business_hours VARCHAR(100) DEFAULT '',
        image VARCHAR(500) DEFAULT '',
        rating DECIMAL(3,2) DEFAULT 5.00,
        is_active TINYINT DEFAULT 1,
        sort_order INT DEFAULT 0,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4''',

    'business_application_types': '''CREATE TABLE IF NOT EXISTS business_application_types (
        id INT AUTO_INCREMENT PRIMARY KEY,
        type_code VARCHAR(50) NOT NULL UNIQUE,
        type_name VARCHAR(100) NOT NULL,
        icon VARCHAR(50) DEFAULT '',
        category VARCHAR(50) DEFAULT 'general',
        description TEXT,
        form_schema TEXT,
        require_attachment TINYINT DEFAULT 0,
        max_attachment INT DEFAULT 9,
        is_active TINYINT DEFAULT 1,
        sort_order INT DEFAULT 0,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4''',

    'business_promotions': '''CREATE TABLE IF NOT EXISTS business_promotions (
        id INT AUTO_INCREMENT PRIMARY KEY,
        name VARCHAR(200) NOT NULL,
        type VARCHAR(50) DEFAULT 'discount',
        description TEXT,
        discount_value DECIMAL(10,2) DEFAULT 0,
        min_amount DECIMAL(10,2) DEFAULT 0,
        start_time DATETIME DEFAULT NULL,
        end_time DATETIME DEFAULT NULL,
        status VARCHAR(20) DEFAULT 'active',
        image VARCHAR(500) DEFAULT '',
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4''',
}

with conn.cursor() as cur:
    for table, sql in tables_sql.items():
        try:
            cur.execute(sql)
            print(f'OK: {table}')
        except Exception as e:
            print(f'ERR {table}: {e}')
conn.commit()
conn.close()
print('\nDone')
