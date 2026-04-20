import pymysql

conn = pymysql.connect(
    host='47.98.238.209',
    user='root',
    password='Wojiacloud$2023',
    database='visit_system',
    charset='utf8mb4'
)
cur = conn.cursor()

# Check products table
cur.execute('SHOW TABLES LIKE "business_products"')
print('products table exists:', bool(cur.fetchone()))

cur.execute('DESCRIBE business_products')
cols = [r[0] for r in cur.fetchall()]
print('Columns:', cols)

needed = ['id', 'shop_id', 'product_name', 'category', 'price', 'original_price',
          'stock', 'sales_count', 'status', 'images', 'description', 'sort_order',
          'created_at', 'deleted', 'ec_id', 'project_id']
missing = [n for n in needed if n not in cols]
print('Missing columns:', missing)

# Check shops table
cur.execute('DESCRIBE business_shops')
shop_cols = [r[0] for r in cur.fetchall()]
print('shops Columns:', shop_cols)

conn.close()
print('Done.')
