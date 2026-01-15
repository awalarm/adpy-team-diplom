from models import User, Candidate, Photo, users_to_blacklist
from sqlalchemy.orm import joinedload, Session
import sqlalchemy as sq


class DatabaseAdapter:

    def __init__(self, session: Session):
        self.session = session

    def save_or_update_user(self, user_data: dict):
        """Сохранить или обновить данные пользователя"""
        user = (
            self.session.query(User).filter(
                User.vk_user_id == user_data["id"]
            ).first()
        )

        if user:
            if "age" in user_data:
                user.age = int(user_data["age"])
            if "gender" in user_data:
                user.gender = int(user_data["gender"])
            if "city" in user_data:
                user.city = str(user_data["city"])
        else:
            user = User(
                vk_user_id=int(user_data["id"]),
                age=int(user_data["age"]),
                gender=int(user_data["gender"]),
                city=str(user_data["city"]),
            )
            self.session.add(user)

        self.session.commit()

    def get_user_data(self, user_vk_id: int) -> dict:
        """Вернуть данные пользователя"""
        user = self.session.query(User).filter(
            User.vk_user_id == user_vk_id
        ).first()
        return {"age": user.age, "city": user.city, "gender": user.gender}

    def _get_or_save_candidate(
        self, candidate_data: dict, photos_data: list
    ):
        """Получить или сохранить кандидата"""
        candidate = (
            self.session.query(Candidate)
            .filter(Candidate.vk_user_id == candidate_data["id"])
            .first()
        )

        if not candidate:
            candidate = Candidate(
                vk_user_id=int(candidate_data["id"]),
                first_name=str(candidate_data["first_name"]),
                last_name=str(candidate_data["last_name"]),
                profile_link=str(candidate_data["profile_link"]),
            )
            self.session.add(candidate)
            self.session.flush()

            for photo_data in photos_data:
                photo = Photo(
                    vk_photo_id=photo_data["vk_photo_id"],
                    photo_link=photo_data["photo_link"],
                    candidate_id=candidate.candidate_id,
                )
                self.session.add(photo)

            self.session.commit()

        return candidate

    def add_to_favorites(
        self, user_vk_id: int, candidate_data: dict, photos_data: list
    ):
        """Добавить кандидата в избранное"""
        user = self.session.query(User).filter(
            User.vk_user_id == user_vk_id
        ).first()

        candidate = self._get_or_save_candidate(candidate_data, photos_data)

        if candidate not in user.favorites:
            user.favorites.append(candidate)
            self.session.commit()

    def get_favorites(self, user_vk_id: int) -> list:
        """Вернуть список избранных кандидатов"""
        user = (
            self.session.query(User)
            .filter(User.vk_user_id == user_vk_id)
            .options(joinedload(User.favorites).joinedload(Candidate.photos))
            .first()
        )

        if not user:
            return []

        favorites = []
        for candidate in user.favorites:
            favorites.append(
                {
                    "vk_user_id": candidate.vk_user_id,
                    "first_name": candidate.first_name,
                    "last_name": candidate.last_name,
                    "profile_link": candidate.profile_link,
                    "photos": [
                        {
                            "photo_link": photo.photo_link,
                            "likes": photo.likes_count,
                            "vk_photo_id": photo.vk_photo_id,
                        }
                        for photo in candidate.photos
                    ],
                }
            )

        return favorites

    def remove_from_favorites(self, user_vk_id: int, candidate_vk_id: int):
        """Убрать кандидата из избранного"""
        user = self.session.query(User).filter(
            User.vk_user_id == user_vk_id
        ).first()

        candidate = (
            self.session.query(Candidate)
            .filter(Candidate.vk_user_id == candidate_vk_id)
            .first()
        )

        if candidate in user.favorites:
            user.favorite_candidates.remove(candidate)
            self.session.commit()

    def add_to_blacklist(self, user_vk_id: int, candidate_vk_id: int):
        """Добавить кандидата в черный список"""
        user = self.session.query(User).filter(
            User.vk_user_id == user_vk_id
        ).first()

        if not user:
            return False

        blocked_candidate = self.session.execute(
            sq.select(users_to_blacklist).where(
                (users_to_blacklist.c.user_id == user.user_id)
                & (users_to_blacklist.c.candidate_vk_id == candidate_vk_id)
            )
        ).first()

        if not blocked_candidate:
            self.session.execute(
                users_to_blacklist.insert().values(
                    user_id=user.user_id, candidate_vk_id=candidate_vk_id
                )
            )
            self.session.commit()
            return True

        return False

    def is_in_blacklist(self, user_vk_id: int, candidate_vk_id: int) -> bool:
        """Проверить, находится ли кандидат в черном списке"""
        user = self.session.query(User).filter(
            User.vk_user_id == user_vk_id
        ).first()

        if not user:
            return False

        blocked_candidate = self.session.execute(
            sq.select(users_to_blacklist.c.user_id).where(
                (users_to_blacklist.c.user_id == user.user_id)
                & (users_to_blacklist.c.candidate_vk_id == candidate_vk_id)
            )
        ).scalar()

        return blocked_candidate is not None
