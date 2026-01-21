import os

DB_USER = os.getenv('DB_USER', 'postgres')
DB_PASSWORD = os.getenv('DB_PASSWORD', 'postgres')
DB_NAME = os.getenv('DB_NAME', 'postgres')
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = os.getenv('DB_PORT', '5432')

DSN = f'postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}'
# DSN = "sqlite:///vk_database.db"

token_vk = ('vk1.a.Ac2wjxQv8Vrfg5rWOiFkhSU7rrK3veIWN7tyr7tMYLMK-Gf85SVOGM6NO'
            '-n3hFc4BxOShSMQCEL-2mwAdiGeLqOEhvdqNXWl3OuIPeIbU92uEPa0xzP7MXzx8z'
            'EGJBSAzWMwaR6YpFmHgkMgsAzHqJUagzCFk7y-QWcF1F9KHDoDFNElUDUC6q_vBZk'
            'x5uku736H0Iot7RPbNGAsRo52eg')

ACCESS_TOKEN_VK = ('vk1.a.0LXAnkhAlhqXXtmZEDfrbjh50F6mn6MIxgvayhlDJvCQyMjeSJAF'
                   'N_NshhwFRT5hns3QtJeQ8Xx0dhRzXBJaRg5iHCbu1Whnxus702tUCIZOW'
                   'tydCcLgfD6fz-JKiC7EgGdn97JnCLewJMVKTqWbzEMpumj130GGYF9WR'
                   'qZCX85BYYG8_YBnvCi6coRnhDcB')
