#!/usr/bin/env python3
import pymysql

try:
    conn = pymysql.connect(
        host='localhost',
        port=3306,
        user='root',
        password='Wojiacloud$2023',
        database='visit_system',
        charset='utf8mb4'
    )
    with conn.cursor() as cursor:
        # Drop old table
        cursor.execute('DROP TABLE IF EXISTS business_notifications')
        # Create with correct schema
        cursor.execute('''CREATE TABLE business_notifications (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT NOT NULL,
            title VARCHAR(200) NOT NULL DEFAULT '',
            content TEXT,
            notify_type VARCHAR(50) DEFAULT 'system',
            is_read TINYINT DEFAULT 0,
            read_at DATETIME DEFAULT NULL,
            ref_id INT DEFAULT NULL,
            ref_type VARCHAR(50) DEFAULT NULL,
            deleted TINYINT DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4''')
    conn.commit()
    conn.close()
    print('OK - business_notifications table recreated with correct schema')
except Exception as e:
    print(f'Error: {e}')
