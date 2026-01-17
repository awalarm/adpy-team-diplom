import psycopg2
from psycopg2 import sql, OperationalError


def create_database(db_name, user, password, host="localhost", port=5432):
    """Создание базы данных. Подключение идет к системе БД 'postgres'"""
    try:
        conn = psycopg2.connect(
            dbname="postgres",
            user=user,
            password=password,
            host=host,
            port=port,
        )
        conn.autocommit = True
        cursor = conn.cursor()

        cursor.execute(
            sql.SQL("CREATE DATABASE {}").format(sql.Identifier(db_name))
        )

        print(f"База данных '{db_name}' успешно создана.")

        cursor.close()
        conn.close()
    except OperationalError as e:
        print(f"Ошибка подключения: {e}")
    except psycopg2.errors.DuplicateDatabase:
        print(f"База данных '{db_name}'уже существует")
    except Exception as e:
        print(f"Ошибка: {e}")
