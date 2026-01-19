import os

DB_USER = os.getenv('DB_USER', 'postgres')
DB_PASSWORD = os.getenv('DB_PASSWORD', 'postgres')
DB_NAME = os.getenv('DB_NAME', 'Enter_db_name')
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = os.getenv('DB_PORT', '5432')

DSN = f'postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}'

token_vk = ('vk1.a.Ac2wjxQv8Vrfg5rWOiFkhSU7rrK3veIWN7tyr7tMYLMK-Gf85SVOGM6NO'
            '-n3hFc4BxOShSMQCEL-2mwAdiGeLqOEhvdqNXWl3OuIPeIbU92uEPa0xzP7MXzx8z'
            'EGJBSAzWMwaR6YpFmHgkMgsAzHqJUagzCFk7y-QWcF1F9KHDoDFNElUDUC6q_vBZk'
            'x5uku736H0Iot7RPbNGAsRo52eg')

ACCESS_TOKEN_VK = ('vk1.a.7OSvjAV4-hB0GTsSBrW3_3ecRiOqSv56_yPT8gyqCvwk94kd4TPA'
                   'BhfoRAIgqULu25iY5pZ3fd4b2Ugwx506Hg_ycZst4CPKekRVO1CA79WsC8'
                   'it5KzkonQZdyTh6gLcAKg1fFBfJiPi6-OnrizmeFjyKmQKQEWummQKvXCi'
                   'cMGoOrgOKTevdWUyP6n1wuJL')


user_id = 618588377
# Для отладки. В релизе закоментирвоать строку снизу и
# раскоментировать строку сверху
# DSN = "sqlite:///vk_database.db"
