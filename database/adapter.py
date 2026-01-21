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

    def get_next_candidate(self, searcher_vk_id: int) -> Optional[dict]:
        """Получить следующего кандидата"""
        user = self._get_user_by_vk_id(searcher_vk_id)
        if not user:
            return None

        # Сначала сбрасываем статус CURRENT у всех кандидатов пользователя
        self.session.execute(
            candidate_to_user.update().where(
                sq.and_(
                    candidate_to_user.c.searcher_vk_id == user.id,
                    candidate_to_user.c.view_status == self.STATUS_CURRENT
                )
            ).values(view_status=self.STATUS_VIEWED)
        )

        # Ищем кандидата с нужными статусами
        query = (
            sq.select(Candidate)
            .join(candidate_to_user, Candidate.id == candidate_to_user.c.candidate_id)
            .where(
                sq.and_(
                    candidate_to_user.c.searcher_vk_id == user.id,
                    candidate_to_user.c.view_status == self.STATUS_NOT_VIEWED,
                    candidate_to_user.c.favorite_status == False,
                    candidate_to_user.c.blacklist_status == False
                )
            )
            .order_by(Candidate.id)
            .limit(1)
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
            ).values(view_status=self.STATUS_CURRENT)
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
            .order_by(Candidate.id)
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
                    candidate_to_user.c.favorite_status == False,
                    candidate_to_user.c.blacklist_status == False
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

            # Находим ID кандидатов для удаления
            links_to_delete = self.session.execute(
                sq.select(candidate_to_user.c.candidate_id)
                .where(
                    sq.and_(
                        candidate_to_user.c.searcher_vk_id == user.id,
                        candidate_to_user.c.favorite_status == False,
                        candidate_to_user.c.blacklist_status == False
                    )
                )
            ).fetchall()

            deleted_count = 0
            candidate_ids_to_check = []

            for link in links_to_delete:
                candidate_id = link[0]
                candidate_ids_to_check.append(candidate_id)

                # Удаляем связь
                self.session.execute(
                    candidate_to_user.delete().where(
                        sq.and_(
                            candidate_to_user.c.candidate_id == candidate_id,
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
                    candidate_to_user.c.favorite_status == True
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
                    candidate_to_user.c.blacklist_status == True
                )
            )
        )

        return self.session.execute(query).scalar()

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

        try:
            links_to_delete = self.session.execute(
                sq.select(candidate_to_user.c.candidate_id)
                .where(
                    sq.and_(
                        candidate_to_user.c.searcher_vk_id == user.id,
                        candidate_to_user.c.view_status == self.STATUS_VIEWED,
                        candidate_to_user.c.favorite_status == False,
                        candidate_to_user.c.blacklist_status == False
                    )
                )
            ).fetchall()

            deleted_count = 0
            candidate_ids_to_check = []

            for link in links_to_delete:
                candidate_id = link[0]
                candidate_ids_to_check.append(candidate_id)

                self.session.execute(
                    candidate_to_user.delete().where(
                        sq.and_(
                            candidate_to_user.c.candidate_id == candidate_id,
                            candidate_to_user.c.searcher_vk_id == user.id
                        )
                    )
                )
                deleted_count += 1

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
            print(f"Ошибка в delete_viewed_candidates: {e}")
            self.session.rollback()
            return 0

    def get_next_favorite(self, searcher_vk_id: int) -> Optional[dict]:
        """Получить следующего непросмотренного фаворита через статусы"""
        user = self._get_user_by_vk_id(searcher_vk_id)
        if not user:
            return None

        # Сначала сбрасываем статус CURRENT у всех фаворитов этого пользователя
        self.session.execute(
            candidate_to_user.update().where(
                sq.and_(
                    candidate_to_user.c.searcher_vk_id == user.id,
                    candidate_to_user.c.favorite_status == True,
                    candidate_to_user.c.view_status == self.STATUS_CURRENT
                )
            ).values(view_status=self.STATUS_VIEWED)
        )

        # Ищем фаворита со статусом NOT_VIEWED
        query = (
            sq.select(Candidate)
            .join(candidate_to_user, Candidate.id == candidate_to_user.c.candidate_id)
            .where(
                sq.and_(
                    candidate_to_user.c.searcher_vk_id == user.id,
                    candidate_to_user.c.favorite_status == True,
                    candidate_to_user.c.view_status == self.STATUS_NOT_VIEWED
                )
            )
            .order_by(Candidate.id)
            .limit(1)
        )

        candidate = self.session.execute(query).scalar()

        if not candidate:
            # Если все просмотрены, сбрасываем статусы и начинаем сначала
            self.reset_favorites_only_view(searcher_vk_id)

            # Повторяем поиск
            candidate = self.session.execute(query).scalar()
            if not candidate:
                return None

        # Помечаем найденного как текущий
        self.session.execute(
            candidate_to_user.update().where(
                sq.and_(
                    candidate_to_user.c.candidate_id == candidate.id,
                    candidate_to_user.c.searcher_vk_id == user.id
                )
            ).values(view_status=self.STATUS_CURRENT)
        )

        self.session.commit()
        return self._prepare_candidate_data(candidate, searcher_vk_id)

    def get_current_favorite(self, user_id: int) -> Optional[dict]:
        """Получить текущего фаворита"""
        user = self._get_user_by_vk_id(user_id)
        if not user:
            return None

        query = (
            sq.select(Candidate)
            .join(candidate_to_user, Candidate.id == candidate_to_user.c.candidate_id)
            .where(
                sq.and_(
                    candidate_to_user.c.searcher_vk_id == user.id,
                    candidate_to_user.c.favorite_status == True,
                    candidate_to_user.c.view_status == self.STATUS_CURRENT
                )
            )
        )

        candidate = self.session.execute(query).scalar()
        if not candidate:
            return None

        return self._prepare_candidate_data(candidate, user_id)

    def mark_favorite_as_viewed(self, user_id: int, candidate_vk_id: int) -> bool:
        """Пометить фаворита как просмотренного"""
        user = self._get_user_by_vk_id(user_id)
        candidate = self._get_candidate_by_vk_id(candidate_vk_id)

        if not user or not candidate:
            return False

        link_entry = self._get_candidate_to_user_entry(candidate.id, user.id)
        if not link_entry or not link_entry.get('favorite_status'):
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

    def reset_favorites_only_view(self, user_id: int):
        """Сбросить статус просмотра только у фаворитов"""
        user = self._get_user_by_vk_id(user_id)
        if not user:
            return

        self.session.execute(
            candidate_to_user.update().where(
                sq.and_(
                    candidate_to_user.c.searcher_vk_id == user.id,
                    candidate_to_user.c.favorite_status == True
                )
            ).values(view_status=self.STATUS_NOT_VIEWED)
        )
        self.session.commit()

    def get_next_blacklist(self, searcher_vk_id: int) -> Optional[dict]:
        """Получить следующего непросмотренного в черном списке через статусы"""
        user = self._get_user_by_vk_id(searcher_vk_id)
        if not user:
            return None

        # Сначала сбрасываем статус CURRENT у всех в черном списке
        self.session.execute(
            candidate_to_user.update().where(
                sq.and_(
                    candidate_to_user.c.searcher_vk_id == user.id,
                    candidate_to_user.c.blacklist_status == True,
                    candidate_to_user.c.view_status == self.STATUS_CURRENT
                )
            ).values(view_status=self.STATUS_VIEWED)
        )

        # Ищем в черном списке со статусом NOT_VIEWED
        query = (
            sq.select(Candidate)
            .join(candidate_to_user, Candidate.id == candidate_to_user.c.candidate_id)
            .where(
                sq.and_(
                    candidate_to_user.c.searcher_vk_id == user.id,
                    candidate_to_user.c.blacklist_status == True,
                    candidate_to_user.c.view_status == self.STATUS_NOT_VIEWED
                )
            )
            .order_by(Candidate.id)
            .limit(1)
        )

        candidate = self.session.execute(query).scalar()

        if not candidate:
            # Если все просмотрены, сбрасываем статусы и начинаем сначала
            self.reset_blacklist_only_view(searcher_vk_id)

            # Повторяем поиск
            candidate = self.session.execute(query).scalar()
            if not candidate:
                return None

        # Помечаем найденного как текущий
        self.session.execute(
            candidate_to_user.update().where(
                sq.and_(
                    candidate_to_user.c.candidate_id == candidate.id,
                    candidate_to_user.c.searcher_vk_id == user.id
                )
            ).values(view_status=self.STATUS_CURRENT)
        )

        self.session.commit()
        return self._prepare_candidate_data(candidate, searcher_vk_id)

    def get_current_blacklist(self, user_id: int) -> Optional[dict]:
        """Получить текущего кандидата в черном списке"""
        user = self._get_user_by_vk_id(user_id)
        if not user:
            return None

        query = (
            sq.select(Candidate)
            .join(candidate_to_user, Candidate.id == candidate_to_user.c.candidate_id)
            .where(
                sq.and_(
                    candidate_to_user.c.searcher_vk_id == user.id,
                    candidate_to_user.c.blacklist_status == True,
                    candidate_to_user.c.view_status == self.STATUS_CURRENT
                )
            )
        )

        candidate = self.session.execute(query).scalar()
        if not candidate:
            return None

        return self._prepare_candidate_data(candidate, user_id)

    def mark_blacklist_as_viewed(self, user_id: int, candidate_vk_id: int) -> bool:
        """Пометить кандидата из черного списка как просмотренного"""
        user = self._get_user_by_vk_id(user_id)
        candidate = self._get_candidate_by_vk_id(candidate_vk_id)

        if not user or not candidate:
            return False

        link_entry = self._get_candidate_to_user_entry(candidate.id, user.id)
        if not link_entry or not link_entry.get('blacklist_status'):
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

    def reset_blacklist_only_view(self, user_id: int):
        """Сбросить статус просмотра только у черного списка"""
        user = self._get_user_by_vk_id(user_id)
        if not user:
            return

        self.session.execute(
            candidate_to_user.update().where(
                sq.and_(
                    candidate_to_user.c.searcher_vk_id == user.id,
                    candidate_to_user.c.blacklist_status == True
                )
            ).values(view_status=self.STATUS_NOT_VIEWED)
        )
        self.session.commit()
