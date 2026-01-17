import os

DB_USER = os.getenv('DB_USER', 'postgres')
DB_PASSWORD = os.getenv('DB_PASSWORD', 'Enter_your_password')
DB_NAME = os.getenv('DB_NAME', 'Enter_db_name')
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = os.getenv('DB_PORT', '5432')

# DSN = f'postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}'

# Для отладки. В релизе закоментирвоать строку снизу и
# раскоментировать строку сверху
DSN = "sqlite:///vk_database.db"
