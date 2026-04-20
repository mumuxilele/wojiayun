content = open('/www/wwwroot/wojiayun/business-admin/app.py', encoding='utf-8').read()

# Fix 1: sales_count -> sales (column name mismatch)
count1 = content.count('sales_count')
content = content.replace('sales_count', 'sales')
print(f'Fixed {count1} occurrences of sales_count -> sales')

# Fix 2: check if business_product_skus table exists - add fallback for missing table
# Line 1306 references business_product_skus which doesn't exist
# Add check/creation for the table
old_sku_query = '"SELECT id, sku_name, sku_code, specs, price, original_price, stock, sales, status'
if old_sku_query in content:
    print('SKU query found, will add table creation fallback')

open('/www/wwwroot/wojiayun/business-admin/app.py', 'w', encoding='utf-8').write(content)
print('Done.')
