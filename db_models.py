import sqlalchemy as sq
from sqlalchemy.orm import declarative_base, relationship


Base = declarative_base()

#Model BD
class Candidates(Base):
    __tablename__ = 'candidates'

    id = sq.Column(sq.Integer, primary_key=True)
    vk_id = sq.Column(sq.Integer, unique=True, nullable=False)
    first_name = sq.Column(sq.String, nullable=False)
    last_name = sq.Column(sq.String, nullable=False)
    age = sq.Column(sq.Integer, unique=True, nullable=False)
    gender = sq.Column(sq.String, nullable= False)
    city = sq.Column(sq.String, nullable=False)
    profile_link = sq.Column(sq.String, nullable=False)

    favorites = relationship('user', secondary='users_to_favorites', backref='candidates')
    blacklist = relationship('user', secondary='users_to_blacklist', backref='candidates')



class User(Base):
    __tablename__ = 'user'

    id = sq.Column(sq.Integer, primary_key=True)
    vk_id = sq.Column(sq.Integer, unique=True, nullable=False)
    age = sq.Column(sq.Integer, unique=True, nullable=False)
    gender = sq.Column(sq.String, nullable= False)
    city = sq.Column(sq.String, nullable=False)



class Photo(Base):
    __tablename__ = 'photo'
    id = sq.Column(sq.Integer, primary_key=True)
    vk_id = sq.Column(sq.Integer, unique=True, nullable=False)
    candidates_id = sq.Column(sq.Integer, sq.ForeignKey('candidates.id'), nullable=False)
    likes_count = sq.Column(sq.Integer, unique=True, nullable=False)
    photo_link = sq.Column(sq.String, nullable=False)

    candidates = relationship('candidates', backref='photo')


def create_tables(engine):
    # Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)

