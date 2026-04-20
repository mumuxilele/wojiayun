import pymysql

conn = pymysql.connect(
    host='47.98.238.209',
    user='root',
    password='Wojiacloud$2023',
    database='visit_system',
    charset='utf8mb4'
)
cur = conn.cursor()

# Check business_products columns
cur.execute('DESCRIBE business_products')
cols = {r[0]: r for r in cur.fetchall()}
print('business_products columns:', list(cols.keys()))

# Check business_product_skus columns  
cur.execute('SHOW TABLES LIKE "business_product_skus"')
if cur.fetchone():
    cur.execute('DESCRIBE business_product_skus')
    sku_cols = [r[0] for r in cur.fetchall()]
    print('business_product_skus columns:', sku_cols)
else:
    print('business_product_skus table does not exist')

conn.close()
