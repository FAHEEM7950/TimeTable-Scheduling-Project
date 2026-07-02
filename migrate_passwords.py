import mysql.connector
from werkzeug.security import generate_password_hash
import os

# Read DB connection details from env or default
DB_CONFIG = {
    'host': os.environ.get("DB_HOST", "localhost"),
    'user': os.environ.get("DB_USER", "root"),
    'password': os.environ.get("DB_PASSWORD", "@Faheem7950"),
    'database': os.environ.get("DB_NAME", "timetable_db")
}

def migrate_passwords():
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)
    except Exception as e:
        print(f"Failed to connect to database: {e}")
        return

    tables = ['colleges', 'developers', 'admin', 'students', 'faculty']
    
    for table in tables:
        print(f"Migrating passwords in table: {table}")
        cursor.execute(f"SELECT id, password FROM {table}")
        rows = cursor.fetchall()
        
        updated_count = 0
        for row in rows:
            pwd = row['password']
            # Check if password is already hashed (pbkdf2:sha256 or scrypt hashes usually start with a specific format)
            if pwd.startswith('pbkdf2:sha256:') or pwd.startswith('scrypt:'):
                continue
            
            hashed_pwd = generate_password_hash(pwd)
            cursor.execute(
                f"UPDATE {table} SET password = %s WHERE id = %s",
                (hashed_pwd, row['id'])
            )
            updated_count += 1
            
        conn.commit()
        print(f"Updated {updated_count} passwords in {table}.")

    cursor.close()
    conn.close()
    print("Migration completed successfully!")

if __name__ == "__main__":
    migrate_passwords()
