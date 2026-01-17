import sqlalchemy
from sqlalchemy.orm import sessionmaker
from config import DSN, DB_NAME, DB_USER, DB_PASSWORD, DB_HOST, DB_PORT
from database.create_database import create_database
from database.db_models import create_tables
from database.adapter import DatabaseAdapter
from vk_bot_api.vk_bot import run_bot


if __name__ == "__main__":
    print("Запуск vk бота для знакомств")

    if not create_database(DB_NAME, DB_USER, DB_PASSWORD, DB_HOST, DB_PORT):
        print("Проблема с базой данных.")
        exit(1)

    try:
        engine = sqlalchemy.create_engine(DSN)
        create_tables(engine)
        print(f"Таблицы созданы в БД '{DB_NAME}'")

        Session = sessionmaker(bind=engine)
        session = Session()

        adapter = DatabaseAdapter(session)

        print("Запускаем бота...")

        run_bot(adapter)

    except Exception as e:
        print(f"Ошибка: {e}")
        import traceback

        traceback.print_exc()
    finally:
        if 'session' in locals():
            session.close()
