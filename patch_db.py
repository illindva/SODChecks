import sqlite3
import os

db_path = os.path.join(os.path.dirname(__file__), 'healthchecks.db')

def patch():
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    columns_to_add = [
        ("description", "TEXT"),
        ("dashboard_name", "VARCHAR(50) DEFAULT 'US SOD'"),
        ("os_type", "VARCHAR(20) DEFAULT 'linux'"),
        ("encrypted_password", "VARCHAR(500)")
    ]
    
    for col_name, col_type in columns_to_add:
        try:
            cursor.execute(f"ALTER TABLE health_check ADD COLUMN {col_name} {col_type}")
            print(f"Added column {col_name}")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e).lower():
                print(f"Column {col_name} already exists.")
            else:
                print(f"Error adding {col_name}: {e}")
                
    conn.commit()
    conn.close()

if __name__ == '__main__':
    patch()
