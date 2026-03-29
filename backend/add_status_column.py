import sqlite3

conn = sqlite3.connect('../database/complaints.db')
cursor = conn.cursor()

cursor.execute("""
ALTER TABLE complaints
ADD COLUMN category TEXT DEFAULT 'General'
""")

conn.commit()
conn.close()

print("Category column added successfully")