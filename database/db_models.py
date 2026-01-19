import sqlalchemy as sq
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class Candidate(Base):
    __tablename__ = "candidates"

    candidate_id = sq.Column(sq.Integer, primary_key=True)
    vk_user_id = sq.Column(sq.Integer, unique=True, nullable=False)
    first_name = sq.Column(sq.String, nullable=False)
    last_name = sq.Column(sq.String, nullable=False)
    profile_link = sq.Column(sq.String, nullable=False)

    favorites = relationship(
        "User", secondary="candidate_to_user", backref="favorite_candidates"
    )


class User(Base):
    __tablename__ = "users"

    searcher_vk_id = sq.Column(sq.Integer, primary_key=True)
    vk_user_id = sq.Column(sq.Integer, unique=True, nullable=False)
    age = sq.Column(sq.Integer, nullable=False)
    gender = sq.Column(sq.Integer, nullable=False)
    city = sq.Column(sq.String, nullable=False)


class Photo(Base):
    __tablename__ = "photos"

    photo_id = sq.Column(sq.Integer, primary_key=True)
    vk_photo_id = sq.Column(sq.Integer, unique=True, nullable=False)
    candidates_id = sq.Column(
        sq.Integer, sq.ForeignKey("candidates.candidate_id"), nullable=False
    )
    photo_link = sq.Column(sq.String, nullable=False)

    candidates = relationship("Candidate", backref="photos")


candidate_to_user = sq.Table(
    "candidate_to_user",
    Base.metadata,
    sq.Column(
        "candidate_id",
        sq.Integer,
        sq.ForeignKey("candidates.candidate_id"),
    ),
    sq.Column(
        "searcher_vk_id", sq.Integer, sq.ForeignKey("users.searcher_vk_id")
    ),
    sq.Column("view_status", sq.Integer, nullable=False),
    sq.Column("favorite_status", sq.Integer, nullable=False),
    sq.Column("blacklist_status", sq.Integer, nullable=False),
)


def create_tables(engine):
    Base.metadata.create_all(engine)
