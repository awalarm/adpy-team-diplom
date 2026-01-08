import sqlalchemy as sq
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class Candidate(Base):
    __tablename__ = "candidates"

    candidate_id = sq.Column(sq.Integer, primary_key=True)
    vk_id = sq.Column(sq.Integer, unique=True, nullable=False)
    first_name = sq.Column(sq.String, nullable=False)
    last_name = sq.Column(sq.String, nullable=False)
    age = sq.Column(sq.Integer, nullable=False)
    gender = sq.Column(sq.String, nullable=False)
    city = sq.Column(sq.String, nullable=False)
    profile_link = sq.Column(sq.String, nullable=False)

    favorites = relationship(
        "User", secondary="users_to_favorites", backref="candidates"
    )
    blacklist = relationship(
        "User", secondary="users_to_blacklist", backref="candidates"
    )


class User(Base):
    __tablename__ = "users"

    user_id = sq.Column(sq.Integer, primary_key=True)
    vk_id = sq.Column(sq.Integer, unique=True, nullable=False)
    age = sq.Column(sq.Integer, nullable=False)
    gender = sq.Column(sq.String, nullable=False)
    city = sq.Column(sq.String, nullable=False)


class Photo(Base):
    __tablename__ = "photos"

    photo_id = sq.Column(sq.Integer, primary_key=True)
    vk_photo_id = sq.Column(sq.Integer, unique=True, nullable=False)
    candidates_id = sq.Column(
        sq.Integer, sq.ForeignKey("candidates.candidate_id"), nullable=False
    )
    likes_count = sq.Column(sq.Integer, nullable=False)
    photo_link = sq.Column(sq.String, nullable=False)

    candidates = relationship("Candidates", backref="photo")


users_to_favorites = sq.Table(
    "users_to_favorites",
    Base.metadata,
    sq.Column(
        "candidates.candidate_id", sq.Integer, sq.ForeignKey("candidates.candidate_id")
    ),
    sq.Column("users.user_id", sq.Integer, sq.ForeignKey("users.user_id")),
)

users_to_blacklist = sq.Table(
    "users_to_blacklist",
    Base.metadata,
    sq.Column(
        "candidates.candidate_id", sq.Integer, sq.ForeignKey("candidates.candidate_id")
    ),
    sq.Column("users.user_id", sq.Integer, sq.ForeignKey("users.user_id")),
)
