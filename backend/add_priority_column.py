import sqlite3

conn = sqlite3.connect('../database/complaints.db')
cursor = conn.cursor()

cursor.execute("""
ALTER TABLE complaints
ADD COLUMN priority TEXT DEFAULT 'Low'
""")

conn.commit()
conn.close()

print("Priority column added")