import sqlalchemy
from sqlalchemy.orm import sessionmaker
from config import DSN
from db_models import create_tables

engine = sqlalchemy.create_engine(DSN)

create_tables(engine)

Session = sessionmaker(bind=engine)
session = Session()

session.close()
