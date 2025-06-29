import sqlite3

conn = sqlite3.connect('xx.sqlite')
cursor = conn.cursor()

# 查看所有表
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
print(cursor.fetchall())

# 查看表结构
cursor.execute("PRAGMA table_info(users);")
print(cursor.fetchall())

# 查看具体数据
cursor.execute("SELECT * FROM tickets;")
rows = cursor.fetchall()
for row in rows:
    print(row)

conn.close()