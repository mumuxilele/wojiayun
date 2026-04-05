"""
V8.0 数据库迁移脚本 - 用户地址簿+商品规格功能
新增表：business_user_addresses, business_product_skus
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from business_common import db

def migrate():
    """执行数据库迁移"""
    print("开始V8.0数据库迁移...")
    
    # 检查并创建用户地址表
    create_addresses_table()
    
    # 检查并创建商品规格表
    create_product_skus_table()
    
    print("V8.0数据库迁移完成!")

def create_addresses_table():
    """创建用户地址簿表"""
    # 检查表是否已存在
    result = db.get_one("""
        SELECT COUNT(*) as cnt FROM information_schema.tables 
        WHERE table_schema=DATABASE() AND table_name='business_user_addresses'
    """)
    
    if result and result['cnt'] > 0:
        print("表 business_user_addresses 已存在，跳过创建")
        return
    
    # 创建用户地址表
    sql = """
    CREATE TABLE IF NOT EXISTS business_user_addresses (
        id INT AUTO_INCREMENT PRIMARY KEY,
        user_id VARCHAR(64) NOT NULL COMMENT '用户ID',
        user_name VARCHAR(64) NOT NULL COMMENT '收货人姓名',
        phone VARCHAR(32) NOT NULL COMMENT '联系电话',
        province VARCHAR(64) COMMENT '省份',
        city VARCHAR(64) COMMENT '城市',
        area VARCHAR(64) COMMENT '区域',
        address VARCHAR(512) NOT NULL COMMENT '详细地址',
        is_default TINYINT DEFAULT 0 COMMENT '是否默认地址 0否 1是',
        tag VARCHAR(32) COMMENT '地址标签(家/公司/其他)',
        ec_id VARCHAR(64) COMMENT '企业ID',
        project_id VARCHAR(64) COMMENT '项目ID',
        deleted TINYINT DEFAULT 0 COMMENT '软删除 0正常 1删除',
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        INDEX idx_user_id (user_id),
        INDEX idx_user_scope (user_id, ec_id, project_id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户收货地址表'
    """
    db.execute(sql)
    print("表 business_user_addresses 创建成功")

def create_product_skus_table():
    """创建商品SKU规格表"""
    result = db.get_one("""
        SELECT COUNT(*) as cnt FROM information_schema.tables 
        WHERE table_schema=DATABASE() AND table_name='business_product_skus'
    """)
    
    if result and result['cnt'] > 0:
        print("表 business_product_skus 已存在，跳过创建")
    else:
        # 创建商品SKU表
        sql = """
        CREATE TABLE IF NOT EXISTS business_product_skus (
            id INT AUTO_INCREMENT PRIMARY KEY,
            product_id INT NOT NULL COMMENT '商品ID',
            sku_name VARCHAR(128) NOT NULL COMMENT 'SKU名称(如:红色-L)',
            sku_code VARCHAR(64) COMMENT 'SKU编码',
            specs JSON COMMENT '规格JSON(如:{"color":"红色","size":"L"})',
            price DECIMAL(10,2) DEFAULT 0 COMMENT '价格',
            original_price DECIMAL(10,2) DEFAULT 0 COMMENT '原价',
            stock INT DEFAULT 0 COMMENT '库存',
            sales_count INT DEFAULT 0 COMMENT '销量',
            status TINYINT DEFAULT 1 COMMENT '状态 0下架 1上架',
            ec_id VARCHAR(64) COMMENT '企业ID',
            project_id VARCHAR(64) COMMENT '项目ID',
            deleted TINYINT DEFAULT 0 COMMENT '软删除',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            INDEX idx_product_id (product_id),
            INDEX idx_sku_code (sku_code),
            INDEX idx_product_status (product_id, status)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='商品SKU规格表'
        """
        db.execute(sql)
        print("表 business_product_skus 创建成功")
    
    # 更新购物车表添加SKU字段
    update_cart_table()

def update_cart_table():
    """更新购物车表添加SKU字段"""
    result = db.get_one("""
        SELECT COUNT(*) as cnt FROM information_schema.columns 
        WHERE table_schema=DATABASE() AND table_name='business_cart' AND column_name='sku_id'
    """)
    
    if result and result['cnt'] > 0:
        print("cart表已有sku_id字段")
        return
    
    try:
        db.execute("ALTER TABLE business_cart ADD COLUMN sku_id INT DEFAULT NULL COMMENT 'SKU ID' AFTER product_id")
        db.execute("ALTER TABLE business_cart ADD COLUMN sku_name VARCHAR(128) DEFAULT NULL COMMENT 'SKU名称' AFTER sku_id")
        print("cart表添加sku_id, sku_name字段成功")
    except Exception as e:
        print(f"cart表添加字段失败: {e}")

if __name__ == '__main__':
    migrate()
