"""
数据库安装脚本
运行此脚本创建数据库和表
"""
import pymysql

# 数据库配置 - 请修改为你的数据库信息
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': 'your_password',  # 修改为你的密码
    'charset': 'utf8mb4'
}

def init_database():
    database_name = 'visit_system'
    
    # 连接数据库
    conn = pymysql.connect(**DB_CONFIG)
    cursor = conn.cursor()
    
    # 创建数据库
    cursor.execute(f"CREATE DATABASE IF NOT EXISTS {database_name} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
    cursor.execute(f"USE {database_name}")
    
    # 创建走访记录表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS visit_records (
            id BIGINT PRIMARY KEY AUTO_INCREMENT,
            company_name VARCHAR(255) NOT NULL COMMENT '企业名称',
            region VARCHAR(255) COMMENT '区域地址',
            staff_id VARCHAR(64) COMMENT '企服人员ID',
            staff_name VARCHAR(64) NOT NULL COMMENT '企服人员姓名',
            visit_date DATE NOT NULL COMMENT '走访日期',
            category VARCHAR(32) COMMENT '沟通事项分类',
            content TEXT COMMENT '沟通详情',
            
            create_by VARCHAR(64) COMMENT '新增人',
            create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '新增时间',
            update_by VARCHAR(64) COMMENT '修改人',
            update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '修改时间',
            delete_by VARCHAR(64) COMMENT '删除人',
            delete_time DATETIME COMMENT '删除时间',
            deleted TINYINT DEFAULT 0 COMMENT '删除状态 0正常 1已删除',
            
            INDEX idx_staff_id (staff_id),
            INDEX idx_visit_date (visit_date),
            INDEX idx_deleted (deleted)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='走访记录表'
    ''')
    
    conn.commit()
    print(f"✅ 数据库 {database_name} 初始化完成!")
    
    cursor.close()
    conn.close()

if __name__ == '__main__':
    init_database()
