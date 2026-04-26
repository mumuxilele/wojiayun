import pymysql
db = pymysql.connect(host='127.0.0.1', user='root', password='Wojiacloud$2023', database='visit_system')
c = db.cursor()
c.execute('DESC yzj_messages')
for r in c.fetchall():
    print(r)
db.close()
