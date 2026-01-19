from database.db_models import User, Candidate, Photo, candidate_to_user
from sqlalchemy.orm import Session
import sqlalchemy as sq
from typing import Optional, List, Dict, Any


class DatabaseAdapter:
    # Константы для статусов
    STATUS_NOT_VIEWED = 0
    STATUS_VIEWED = 1
    STATUS_CURRENT = 2

    def __init__(self, session: Session):
        self.session = session

    def save_or_update_user(self, user_data: dict) -> User:
        """Сохранить или обновить данные пользователя"""
        user = self.session.query(User).filter(
            User.vk_user_id == user_data["vk_user_id"]
        ).first()

        if user:
            user.age = int(user_data["age"])
            user.gender = int(user_data["gender"])
            user.city = str(user_data["city"])
        else:
            user = User(
                vk_user_id=int(user_data["vk_user_id"]),
                age=int(user_data["age"]),
                gender=int(user_data["gender"]),
                city=str(user_data["city"])
            )
            self.session.add(user)

        self.session.commit()
        return user

    def get_user_data(self, user_vk_id: int) -> dict:
        """Вернуть данные пользователя"""
        user = self.session.query(User).filter(
            User.vk_user_id == user_vk_id
        ).first()

        if user:
            return {
                "vk_user_id": user.vk_user_id,
                "age": user.age,
                "city": user.city,
                "gender": user.gender
            }
        return {}

    def _get_candidate_to_user_entry(self, candidate_id: int, searcher_vk_id: int) -> Optional[dict]:
        """Получить запись из связующей таблицы"""
        result = self.session.execute(
            sq.select(candidate_to_user).where(
                sq.and_(
                    candidate_to_user.c.candidate_id == candidate_id,
                    candidate_to_user.c.searcher_vk_id == searcher_vk_id
                )
            )
        ).first()
        return result._asdict() if result else None

    def _get_candidate_by_vk_id(self, candidate_vk_id: int) -> Optional[Candidate]:
        """Получить кандидата по VK ID"""
        return self.session.query(Candidate).filter(
            Candidate.vk_candidate_id == candidate_vk_id
        ).first()

    def _get_user_by_vk_id(self, user_vk_id: int) -> Optional[User]:
        """Получить пользователя по VK ID"""
        return self.session.query(User).filter(
            User.vk_user_id == user_vk_id
        ).first()

    def save_candidate_with_photos(
            self, candidate_data: dict, photos_data: list, searcher_vk_id: int) -> Candidate:
        """Сохранить кандидата с фото"""
        candidate = self._get_candidate_by_vk_id(candidate_data["id"])

        if not candidate:
            candidate = Candidate(
                vk_candidate_id=int(candidate_data["id"]),
                first_name=str(candidate_data["first_name"]),
                last_name=str(candidate_data["last_name"]),
                profile_link=str(candidate_data["profile_link"]),
            )
            self.session.add(candidate)
            self.session.flush()

        user = self._get_user_by_vk_id(searcher_vk_id)
        if not user:
            raise ValueError(f"Пользователь с VK ID {searcher_vk_id} не найден")

        existing_link = self._get_candidate_to_user_entry(candidate.id, user.id)

        if not existing_link:
            # Создаем связь в связующей таблице
            self.session.execute(
                candidate_to_user.insert().values(
                    candidate_id=candidate.id,
                    searcher_vk_id=user.id,
                    view_status=self.STATUS_NOT_VIEWED,
                    favorite_status=False,
                    blacklist_status=False
                )
            )

        # Сохраняем фото
        for photo_data in photos_data:
            # Проверяем, существует ли уже фото
            existing_photo = self.session.query(Photo).filter(
                Photo.vk_photo_id == photo_data["vk_photo_id"],
                Photo.candidate_id == candidate.id
            ).first()

            if not existing_photo:
                photo = Photo(
                    vk_photo_id=photo_data["vk_photo_id"],
                    candidate_id=candidate.id,
                    photo_link=photo_data["photo_link"],
                )
                self.session.add(photo)

        self.session.commit()
        return candidate

    def _prepare_candidate_data(self, candidate: Candidate, user_id: int) -> Dict[str, Any]:
        """Подготовка данных кандидата"""
        user = self._get_user_by_vk_id(user_id)
        if not user:
            return {}

        link_entry = self._get_candidate_to_user_entry(candidate.id, user.id)

        if not link_entry:
            return {}

        photos = self.session.query(Photo).filter(
            Photo.candidate_id == candidate.id
        ).all()

        photos_data = []
        for photo in photos:
            photos_data.append({
                'vk_photo_id': photo.vk_photo_id,
                'photo_link': photo.photo_link,
                'owner_id': candidate.vk_candidate_id
            })

        return {
            'vk_user_id': candidate.vk_candidate_id,
            'first_name': candidate.first_name,
            'last_name': candidate.last_name,
            'profile_link': candidate.profile_link,
            'view_status': link_entry['view_status'],
            'favorite_status': link_entry['favorite_status'],
            'blacklist_status': link_entry['blacklist_status'],
            'photos': photos_data
        }

    def _reset_current_statuses(self, searcher_vk_id: int):
        """Сбросить статус 'текущий' у всех кандидатов пользователя"""
        user = self._get_user_by_vk_id(searcher_vk_id)
        if not user:
            return

        # Находим все связи где есть статус CURRENT
        links_to_update = self.session.execute(
            sq.select(candidate_to_user).where(
                sq.and_(
                    candidate_to_user.c.searcher_vk_id == user.id,
                    candidate_to_user.c.view_status == self.STATUS_CURRENT
                )
            )
        ).fetchall()

        for link in links_to_update:
            link_dict = link._asdict()
            self.session.execute(
                candidate_to_user.update().where(
                    sq.and_(
                        candidate_to_user.c.candidate_id == link_dict['candidate_id'],
                        candidate_to_user.c.searcher_vk_id == user.id
                    )
                ).values(
                    view_status=self.STATUS_VIEWED
                )
            )

    def get_next_candidate(self, searcher_vk_id: int) -> Optional[dict]:
        """Получить следующего кандидата"""
        user = self._get_user_by_vk_id(searcher_vk_id)
        if not user:
            return None

        self._reset_current_statuses(searcher_vk_id)

        # Ищем кандидата с нужными статусами через связующую таблицу
        query = (
            sq.select(Candidate)
            .join(candidate_to_user, Candidate.id == candidate_to_user.c.candidate_id)
            .where(
                sq.and_(
                    candidate_to_user.c.searcher_vk_id == user.id,
                    candidate_to_user.c.view_status == self.STATUS_NOT_VIEWED,
                    candidate_to_user.c.favorite_status.in_(False),
                    candidate_to_user.c.blacklist_status.in_(False)
                )
            )
        )

        candidate = self.session.execute(query).scalar()

        if not candidate:
            return None

        # Помечаем как текущий
        self.session.execute(
            candidate_to_user.update().where(
                sq.and_(
                    candidate_to_user.c.candidate_id == candidate.id,
                    candidate_to_user.c.searcher_vk_id == user.id
                )
            ).values(
                view_status=self.STATUS_CURRENT
            )
        )

        self.session.commit()
        return self._prepare_candidate_data(candidate, searcher_vk_id)

    def _update_status(
            self, searcher_vk_id: int, candidate_vk_id: int, status_type: str, to_add: bool) -> bool:
        """Общий метод для обновления статусов (избранное/черный список)"""
        user = self._get_user_by_vk_id(searcher_vk_id)
        candidate = self._get_candidate_by_vk_id(candidate_vk_id)

        if not user or not candidate:
            return False

        link_entry = self._get_candidate_to_user_entry(candidate.id, user.id)
        if not link_entry:
            return False

        if status_type == 'favorite':
            status_field = 'favorite_status'
        elif status_type == 'blacklist':
            status_field = 'blacklist_status'
        else:
            raise ValueError(f"Неизвестный тип статуса: {status_type}")

        if to_add:
            # Добавление в список
            self.session.execute(
                candidate_to_user.update().where(
                    sq.and_(
                        candidate_to_user.c.candidate_id == candidate.id,
                        candidate_to_user.c.searcher_vk_id == user.id
                    )
                ).values(
                    **{status_field: True},
                    view_status=self.STATUS_VIEWED
                )
            )
        else:
            # Удаление из списка
            self.session.execute(
                candidate_to_user.update().where(
                    sq.and_(
                        candidate_to_user.c.candidate_id == candidate.id,
                        candidate_to_user.c.searcher_vk_id == user.id
                    )
                ).values(**{status_field: False})
            )

        self.session.commit()
        return True

    def add_to_favorites(self, searcher_vk_id: int, candidate_vk_id: int) -> bool:
        """Добавить кандидата в избранное"""
        return self._update_status(searcher_vk_id, candidate_vk_id, 'favorite', True)

    def remove_from_favorites(self, searcher_vk_id: int, candidate_vk_id: int) -> bool:
        """Убрать кандидата из избранного"""
        return self._update_status(searcher_vk_id, candidate_vk_id, 'favorite', False)

    def add_to_blacklist(self, searcher_vk_id: int, candidate_vk_id: int) -> bool:
        """Добавить кандидата в черный список"""
        return self._update_status(searcher_vk_id, candidate_vk_id, 'blacklist', True)

    def remove_from_blacklist(self, searcher_vk_id: int, candidate_vk_id: int) -> bool:
        """Убрать кандидата из черного списка"""
        return self._update_status(searcher_vk_id, candidate_vk_id, 'blacklist', False)

    def _get_candidates_by_status(
            self, searcher_vk_id: int, status_field: str, status_value: bool) -> List[Dict]:
        """Общий метод для получения кандидатов по статусу"""
        user = self._get_user_by_vk_id(searcher_vk_id)
        if not user:
            return []

        query = (
            sq.select(Candidate)
            .join(candidate_to_user, Candidate.id == candidate_to_user.c.candidate_id)
            .where(
                sq.and_(
                    candidate_to_user.c.searcher_vk_id == user.id,
                    getattr(candidate_to_user.c, status_field) == status_value
                )
            )
        )

        candidates = self.session.execute(query).scalars().all()

        result = []
        for candidate in candidates:
            result.append(self._prepare_candidate_data(candidate, searcher_vk_id))

        return result

    def get_favorites(self, searcher_vk_id: int) -> List[Dict]:
        """Вернуть список избранных кандидатов"""
        return self._get_candidates_by_status(
            searcher_vk_id,
            'favorite_status',
            True
        )

    def get_blacklist(self, searcher_vk_id: int) -> List[Dict]:
        """Вернуть список черного списка"""
        return self._get_candidates_by_status(
            searcher_vk_id,
            'blacklist_status',
            True
        )

    def get_unviewed_candidates_count(self, searcher_vk_id: int) -> int:
        """Получить количество непросмотренных кандидатов"""
        user = self._get_user_by_vk_id(searcher_vk_id)
        if not user:
            return 0

        query = (
            sq.select(sq.func.count())
            .select_from(candidate_to_user)
            .where(
                sq.and_(
                    candidate_to_user.c.searcher_vk_id == user.id,
                    candidate_to_user.c.view_status == self.STATUS_NOT_VIEWED,
                    candidate_to_user.c.favorite_status.in_(False),
                    candidate_to_user.c.blacklist_status.in_(False)
                )
            )
        )

        return self.session.execute(query).scalar()

    def reset_viewed_candidates(self, searcher_vk_id: int):
        """Сбросить статус просмотренных кандидатов"""
        user = self._get_user_by_vk_id(searcher_vk_id)
        if not user:
            return

        # Все просмотренные делаем непросмотренными
        self.session.execute(
            candidate_to_user.update().where(
                sq.and_(
                    candidate_to_user.c.searcher_vk_id == user.id,
                    candidate_to_user.c.view_status.in_([self.STATUS_VIEWED, self.STATUS_CURRENT])
                )
            ).values(view_status=self.STATUS_NOT_VIEWED)
        )

        self.session.commit()

    def delete_candidates_on_parameter_change(self, user_id: int) -> int:
        """Удалить кандидатов пользователя (кроме избранных и черного списка) при изменении параметров"""
        try:
            user = self._get_user_by_vk_id(user_id)
            if not user:
                return 0

            # Находим связи для удаления
            links_to_delete = self.session.execute(
                sq.select(candidate_to_user).where(
                    sq.and_(
                        candidate_to_user.c.searcher_vk_id == user.id,
                        candidate_to_user.c.favorite_status.in_(False),
                        candidate_to_user.c.blacklist_status.in_(False)
                    )
                )
            ).fetchall()

            deleted_count = 0
            candidate_ids_to_check = []

            for link in links_to_delete:
                link_dict = link._asdict()
                candidate_ids_to_check.append(link_dict['candidate_id'])

                # Удаляем связь
                self.session.execute(
                    candidate_to_user.delete().where(
                        sq.and_(
                            candidate_to_user.c.candidate_id == link_dict['candidate_id'],
                            candidate_to_user.c.searcher_vk_id == user.id
                        )
                    )
                )
                deleted_count += 1

            # Проверяем, не используется ли кандидат другими пользователями
            for candidate_id in candidate_ids_to_check:
                other_links = self.session.execute(
                    sq.select(candidate_to_user).where(
                        candidate_to_user.c.candidate_id == candidate_id
                    )
                ).fetchall()

                if not other_links:
                    candidate = self.session.query(Candidate).get(candidate_id)
                    if candidate:
                        self.session.query(Photo).filter(
                            Photo.candidate_id == candidate_id
                        ).delete()
                        self.session.delete(candidate)

            self.session.commit()
            return deleted_count
        except Exception as e:
            print(f"Ошибка при удалении кандидатов: {e}")
            self.session.rollback()
            return 0

    def get_candidates_count_to_delete(self, user_id: int) -> int:
        """Получить количество кандидатов, которые будут удалены при изменении параметров"""
        user = self._get_user_by_vk_id(user_id)
        if not user:
            return 0

        query = (
            sq.select(sq.func.count())
            .select_from(candidate_to_user)
            .where(
                sq.and_(
                    candidate_to_user.c.searcher_vk_id == user.id,
                    candidate_to_user.c.favorite_status.in_(False),
                    candidate_to_user.c.blacklist_status.in_(False)
                )
            )
        )

        return self.session.execute(query).scalar()

    def get_current_candidate(self, user_id: int) -> Optional[dict]:
        """Получить текущего просматриваемого кандидата"""
        user = self._get_user_by_vk_id(user_id)
        if not user:
            return None

        query = (
            sq.select(Candidate)
            .join(candidate_to_user, Candidate.id == candidate_to_user.c.candidate_id)
            .where(
                sq.and_(
                    candidate_to_user.c.searcher_vk_id == user.id,
                    candidate_to_user.c.view_status == self.STATUS_CURRENT
                )
            )
        )

        candidate = self.session.execute(query).scalar()
        if not candidate:
            return None

        return self._prepare_candidate_data(candidate, user_id)

    def mark_candidate_as_viewed(self, user_id: int, candidate_vk_id: int) -> bool:
        """Пометить кандидата как просмотренного"""
        user = self._get_user_by_vk_id(user_id)
        candidate = self._get_candidate_by_vk_id(candidate_vk_id)

        if not user or not candidate:
            return False

        link_entry = self._get_candidate_to_user_entry(candidate.id, user.id)
        if not link_entry:
            return False

        self.session.execute(
            candidate_to_user.update().where(
                sq.and_(
                    candidate_to_user.c.candidate_id == candidate.id,
                    candidate_to_user.c.searcher_vk_id == user.id
                )
            ).values(view_status=self.STATUS_VIEWED)
        )

        self.session.commit()
        return True

    def mark_candidate_as_current(self, user_id: int, candidate_vk_id: int) -> bool:
        """Пометить кандидата как текущий"""
        user = self._get_user_by_vk_id(user_id)
        candidate = self._get_candidate_by_vk_id(candidate_vk_id)

        if not user or not candidate:
            return False

        link_entry = self._get_candidate_to_user_entry(candidate.id, user.id)
        if not link_entry:
            return False

        self.session.execute(
            candidate_to_user.update().where(
                sq.and_(
                    candidate_to_user.c.candidate_id == candidate.id,
                    candidate_to_user.c.searcher_vk_id == user.id
                )
            ).values(view_status=self.STATUS_CURRENT)
        )

        self.session.commit()
        return True

    def get_favorites_count(self, user_id: int) -> int:
        """Получить количество избранных пользователей"""
        user = self._get_user_by_vk_id(user_id)
        if not user:
            return 0

        query = (
            sq.select(sq.func.count())
            .select_from(candidate_to_user)
            .where(
                sq.and_(
                    candidate_to_user.c.searcher_vk_id == user.id,
                    candidate_to_user.c.favorite_status.in_(True)
                )
            )
        )

        return self.session.execute(query).scalar()

    def get_blacklist_count(self, user_id: int) -> int:
        """Получить количество пользователей в черном списке"""
        user = self._get_user_by_vk_id(user_id)
        if not user:
            return 0

        query = (
            sq.select(sq.func.count())
            .select_from(candidate_to_user)
            .where(
                sq.and_(
                    candidate_to_user.c.searcher_vk_id == user.id,
                    candidate_to_user.c.blacklist_status.in_(True)
                )
            )
        )

        return self.session.execute(query).scalar()

    def delete_candidate_completely(self, user_id: int, candidate_vk_id: int) -> bool:
        """Полностью удалить кандидата (с фотографиями)"""
        user = self._get_user_by_vk_id(user_id)
        candidate = self._get_candidate_by_vk_id(candidate_vk_id)

        if not user or not candidate:
            return False

        try:
            # Удаляем связь пользователя с кандидатом
            self.session.execute(
                candidate_to_user.delete().where(
                    sq.and_(
                        candidate_to_user.c.candidate_id == candidate.id,
                        candidate_to_user.c.searcher_vk_id == user.id
                    )
                )
            )

            # Проверяем, не используется ли кандидат другими пользователями
            other_links = self.session.execute(
                sq.select(candidate_to_user).where(
                    candidate_to_user.c.candidate_id == candidate.id
                )
            ).fetchall()

            # Если кандидат не связан ни с одним пользователем, удаляем его и его фото
            if not other_links:
                self.session.query(Photo).filter(
                    Photo.candidate_id == candidate.id
                ).delete()

                self.session.delete(candidate)

            self.session.commit()
            return True

        except Exception as e:
            print(f"Ошибка при удалении кандидата: {e}")
            self.session.rollback()
            return False

    def get_candidates_statistics(self, user_id: int) -> dict:
        """Получить статистику кандидатов"""
        unviewed_count = self.get_unviewed_candidates_count(user_id)
        favorites_count = self.get_favorites_count(user_id)
        blacklist_count = self.get_blacklist_count(user_id)

        return {
            'unviewed': unviewed_count,
            'favorites': favorites_count,
            'blacklist': blacklist_count
        }

    def delete_viewed_candidates(self, user_id: int) -> int:
        """Удалить просмотренных кандидатов (кроме избранных и черного списка)"""
        user = self._get_user_by_vk_id(user_id)
        if not user:
            return 0

        # Находим связи для удаления
        links_to_delete = self.session.execute(
            sq.select(candidate_to_user, Candidate)
            .join(Candidate, candidate_to_user.c.candidate_id == Candidate.id)
            .where(
                sq.and_(
                    candidate_to_user.c.searcher_vk_id == user.id,
                    candidate_to_user.c.view_status == self.STATUS_VIEWED,
                    candidate_to_user.c.favorite_status.in_(False),
                    candidate_to_user.c.blacklist_status.in_(False)
                )
            )
        ).fetchall()

        deleted_count = 0
        candidate_ids_to_check = []

        for link, candidate in links_to_delete:
            candidate_ids_to_check.append(candidate.id)

            # Удаляем связь
            self.session.execute(
                candidate_to_user.delete().where(
                    sq.and_(
                        candidate_to_user.c.candidate_id == candidate.id,
                        candidate_to_user.c.searcher_vk_id == user.id
                    )
                )
            )
            deleted_count += 1

        # Проверяем, не используется ли кандидат другими пользователями
        for candidate_id in candidate_ids_to_check:
            other_links = self.session.execute(
                sq.select(candidate_to_user).where(
                    candidate_to_user.c.candidate_id == candidate_id
                )
            ).fetchall()

            # Если кандидат не связан ни с одним пользователем, удаляем его и его фото
            if not other_links:
                candidate = self.session.query(Candidate).get(candidate_id)
                if candidate:
                    self.session.query(Photo).filter(
                        Photo.candidate_id == candidate_id
                    ).delete()
                    self.session.delete(candidate)

        self.session.commit()
        return deleted_count

    def reset_favorites_view(self, user_id: int):
        """Сбросить статус просмотра избранного пользователя"""
        user = self._get_user_by_vk_id(user_id)
        if not user:
            return

        self.session.execute(
            candidate_to_user.update().where(
                sq.and_(
                    candidate_to_user.c.searcher_vk_id == user.id,
                    candidate_to_user.c.favorite_status.in_(True)
                )
            ).values(view_status=self.STATUS_VIEWED)
        )
        self.session.commit()

    def reset_blacklist_view(self, user_id: int):
        """Сбросить статус просмотра черного списка"""
        user = self._get_user_by_vk_id(user_id)
        if not user:
            return

        self.session.execute(
            candidate_to_user.update().where(
                sq.and_(
                    candidate_to_user.c.searcher_vk_id == user.id,
                    candidate_to_user.c.blacklist_status.in_(True)
                )
            ).values(view_status=self.STATUS_VIEWED)
        )
        self.session.commit()
