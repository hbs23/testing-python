import os
import sqlite3
import hashlib
import pickle

# 1. SQL Injection
username = input("Username: ")
password = input("Password: ")
conn = sqlite3.connect('users.db')
query = f"SELECT * FROM users WHERE username='{username}' AND password='{password}'"
cursor = conn.execute(query)
print(cursor.fetchall())

# 2. Command Injection
filename = input("Enter filename: ")
os.system(f"cat {filename}")

# 3. Hardcoded Secrets
#API_KEY = "1234567890-SECRET-KEY"
API_KEY = "sk_live_51M29Lbq29fb90sFb90fsbfUFSNYgfb091yfBsADS"
# 4. Weak Hash
user_pass = input("Enter your password: ")
hashed = hashlib.md5(user_pass.encode()).hexdigest()
print("Weak hashed:", hashed)

# 5. Broken Authentication
def login(user, password):
    if password == "admin123":
        return True
    return False

# 6. Insecure Deserialization
data = input("Enter serialized data: ")
obj = pickle.loads(data.encode())
print("Decoded:", obj)