from database.db_models import User, Candidate, Photo
from sqlalchemy.orm import Session
import sqlalchemy as sq
from typing import Optional, List, Dict, Any


class DatabaseAdapter:
    # Константы для статусов
    STATUS_NOT_VIEWED = 0
    STATUS_VIEWED = 1
    STATUS_CURRENT = 2
    STATUS_INACTIVE = 3

    def __init__(self, session: Session):
        self.session = session

    def save_or_update_user(self, user_data: dict) -> User:
        """Сохранить или обновить данные пользователя"""
        user = self.session.query(User).get(user_data["vk_user_id"])

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
        user = self.session.query(User).get(user_vk_id)
        if user:
            return {
                "vk_user_id": user.vk_user_id,
                "age": user.age,
                "city": user.city,
                "gender": user.gender
            }
        return {}

    def _get_or_create_candidate(self, candidate_vk_id: int, searcher_vk_id: int) -> Optional[Candidate]:
        """Внутренний метод для получения или создания кандидата"""
        return self.session.query(Candidate).filter(
            Candidate.vk_user_id == candidate_vk_id,
            Candidate.searcher_vk_id == searcher_vk_id
        ).first()

    def save_candidate_with_photos(
            self, candidate_data: dict, photos_data: list, searcher_vk_id: int) -> Candidate:

        """Сохранить кандидата с фото"""
        candidate = self._get_or_create_candidate(
            candidate_data["id"],
            searcher_vk_id
        )

        if candidate:
            return candidate

        candidate = Candidate(
            vk_user_id=int(candidate_data["id"]),
            searcher_vk_id=searcher_vk_id,
            first_name=str(candidate_data["first_name"]),
            last_name=str(candidate_data["last_name"]),
            profile_link=str(candidate_data["profile_link"]),
            view_status=self.STATUS_NOT_VIEWED,
            favorite_status=self.STATUS_NOT_VIEWED,
            blacklist_status=self.STATUS_NOT_VIEWED,
        )
        self.session.add(candidate)
        self.session.flush()

        for photo_data in photos_data:
            photo = Photo(
                vk_photo_id=photo_data["vk_photo_id"],
                photo_link=photo_data["photo_link"],
                candidates_id=candidate.candidate_id,
            )
            self.session.add(photo)

        self.session.commit()
        return candidate

    def _prepare_candidate_data(self, candidate: Candidate) -> Dict[str, Any]:
        """Подготовка данных кандидата"""
        photos = self.session.query(Photo).filter(
            Photo.candidates_id == candidate.candidate_id
        ).all()

        photos_data = []
        for photo in photos:
            photos_data.append({
                'vk_photo_id': photo.vk_photo_id,
                'photo_link': photo.photo_link,
                'owner_id': candidate.vk_user_id
            })

        return {
            'id': candidate.vk_user_id,
            'vk_user_id': candidate.vk_user_id,
            'first_name': candidate.first_name,
            'last_name': candidate.last_name,
            'profile_link': candidate.profile_link,
            'photos': photos_data
        }

    def _reset_current_statuses(self, searcher_vk_id: int):
        """Сбросить статус 'текущий' у всех кандидатов пользователя"""
        self.session.query(Candidate).filter(
            Candidate.searcher_vk_id == searcher_vk_id,
            sq.or_(
                Candidate.view_status == self.STATUS_CURRENT,
                Candidate.favorite_status == self.STATUS_CURRENT,
                Candidate.blacklist_status == self.STATUS_CURRENT
            )
        ).update({
            "view_status": self.STATUS_VIEWED,
            "favorite_status": self.STATUS_INACTIVE,
            "blacklist_status": self.STATUS_INACTIVE
        })

    def get_next_candidate(self, searcher_vk_id: int) -> Optional[dict]:
        """Получить следующего кандидата"""
        # Сбрасываем статус "текущее" у всех кандидатов пользователя
        self._reset_current_statuses(searcher_vk_id)

        # Ищем непросмотренного кандидата
        candidate = self.session.query(Candidate).filter(
            Candidate.searcher_vk_id == searcher_vk_id,
            Candidate.view_status == self.STATUS_NOT_VIEWED,
            Candidate.favorite_status.in_([self.STATUS_NOT_VIEWED, self.STATUS_INACTIVE]),
            Candidate.blacklist_status.in_([self.STATUS_NOT_VIEWED, self.STATUS_INACTIVE])
        ).first()

        if not candidate:
            return None

        # Помечаем как текущий
        candidate.view_status = self.STATUS_CURRENT

        if candidate.favorite_status in [self.STATUS_VIEWED, self.STATUS_INACTIVE]:
            candidate.favorite_status = self.STATUS_CURRENT

        if candidate.blacklist_status in [self.STATUS_VIEWED, self.STATUS_INACTIVE]:
            candidate.blacklist_status = self.STATUS_CURRENT

        self.session.commit()
        return self._prepare_candidate_data(candidate)

    def _update_status(self, searcher_vk_id: int, candidate_vk_id: int,
                       status_type: str, to_add: bool) -> bool:
        """Общий метод для обновления статусов (избранное/черный список)"""
        candidate = self._get_or_create_candidate(candidate_vk_id, searcher_vk_id)

        if not candidate:
            return False

        if status_type == 'favorite':
            status_field = 'favorite_status'
        elif status_type == 'blacklist':
            status_field = 'blacklist_status'
        else:
            raise ValueError(f"Неизвестный тип статуса: {status_type}")

        if to_add:
            # Добавление в список
            if candidate.view_status == self.STATUS_CURRENT:
                setattr(candidate, status_field, self.STATUS_CURRENT)
            else:
                setattr(candidate, status_field, self.STATUS_VIEWED)
            candidate.view_status = self.STATUS_VIEWED
        else:
            # Удаление из списка
            current_status = getattr(candidate, status_field)
            if current_status == self.STATUS_CURRENT:
                setattr(candidate, status_field, self.STATUS_INACTIVE)
            elif current_status == self.STATUS_VIEWED:
                setattr(candidate, status_field, self.STATUS_NOT_VIEWED)

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

    def _get_candidates_by_status(self, searcher_vk_id: int,
                                  status_field: str,
                                  status_values: List[int]) -> List[Dict]:
        """Общий метод для получения кандидатов по статусу"""
        candidates = self.session.query(Candidate).filter(
            Candidate.searcher_vk_id == searcher_vk_id,
            getattr(Candidate, status_field).in_(status_values)
        ).all()

        result = []
        for candidate in candidates:
            result.append(self._prepare_candidate_data(candidate))

        return result

    def get_favorites(self, searcher_vk_id: int) -> List[Dict]:
        """Вернуть список избранных кандидатов"""
        return self._get_candidates_by_status(
            searcher_vk_id,
            'favorite_status',
            [self.STATUS_VIEWED, self.STATUS_CURRENT, self.STATUS_INACTIVE]
        )

    def get_blacklist(self, searcher_vk_id: int) -> List[Dict]:
        """Вернуть список черного списка"""
        return self._get_candidates_by_status(
            searcher_vk_id,
            'blacklist_status',
            [self.STATUS_VIEWED, self.STATUS_CURRENT, self.STATUS_INACTIVE]
        )

    def get_unviewed_candidates_count(self, searcher_vk_id: int) -> int:
        """Получить количество непросмотренных кандидатов"""
        return self.session.query(Candidate).filter(
            Candidate.searcher_vk_id == searcher_vk_id,
            Candidate.view_status == self.STATUS_NOT_VIEWED,
            Candidate.favorite_status.in_([self.STATUS_NOT_VIEWED, self.STATUS_INACTIVE]),
            Candidate.blacklist_status.in_([self.STATUS_NOT_VIEWED, self.STATUS_INACTIVE])
        ).count()

    def reset_viewed_candidates(self, searcher_vk_id: int):
        """Сбросить статус просмотренных кандидатов"""
        # Все просмотренные делаем непросмотренными
        self.session.query(Candidate).filter(
            Candidate.searcher_vk_id == searcher_vk_id,
            Candidate.view_status.in_([self.STATUS_VIEWED, self.STATUS_CURRENT])
        ).update({"view_status": self.STATUS_NOT_VIEWED})

        self.session.commit()

    def delete_candidates_on_parameter_change(self, user_id: int) -> int:
        """Удалить кандидатов пользователя (кроме избранных и черного списка) при изменении параметров"""
        try:
            candidates_to_delete = self.session.query(Candidate).filter(
                Candidate.searcher_vk_id == user_id,
                Candidate.favorite_status == 0,
                Candidate.blacklist_status == 0
            ).all()

            deleted_count = 0
            if candidates_to_delete:
                for candidate in candidates_to_delete:
                    # Удаляем фото кандидата
                    self.session.query(Photo).filter(
                        Photo.candidates_id == candidate.candidate_id
                    ).delete()
                    # Удаляем кандидата
                    self.session.delete(candidate)
                    deleted_count += 1

                self.session.commit()
                return deleted_count

            return 0
        except Exception as e:
            print(f"Ошибка при удалении кандидатов: {e}")
            self.session.rollback()
            return 0

    def get_candidates_count_to_delete(self, user_id: int) -> int:
        """Получить количество кандидатов, которые будут удалены при изменении параметров"""
        return self.session.query(Candidate).filter(
            Candidate.searcher_vk_id == user_id,
            Candidate.favorite_status == 0,
            Candidate.blacklist_status == 0
        ).count()

    def get_current_candidate(self, user_id: int):
        """Получить текущего кандидата (со статусом просмотра 2)"""
        candidate = self.session.query(Candidate).filter(
            Candidate.searcher_vk_id == user_id,
            Candidate.view_status == 2,
            Candidate.favorite_status.in_([self.STATUS_NOT_VIEWED, self.STATUS_INACTIVE]),
            Candidate.blacklist_status.in_([self.STATUS_NOT_VIEWED, self.STATUS_INACTIVE])
        ).first()

        if not candidate:
            return None

        return self._prepare_candidate_data(candidate)

    def mark_candidate_as_viewed(self, user_id: int, candidate_vk_id: int) -> bool:
        """Пометить кандидата как просмотренного"""
        candidate = self._get_or_create_candidate(candidate_vk_id, user_id)

        if not candidate:
            return False

        candidate.view_status = self.STATUS_VIEWED
        self.session.commit()
        return True

    def mark_candidate_as_current(self, user_id: int, candidate_vk_id: int) -> bool:
        """Пометить кандидата как текущий"""
        candidate = self._get_or_create_candidate(candidate_vk_id, user_id)

        if not candidate:
            return False

        candidate.view_status = self.STATUS_CURRENT
        self.session.commit()
        return True

    def get_favorites_count(self, user_id: int) -> int:
        """Получить количество фаворитов"""
        return self.session.query(Candidate).filter(
            Candidate.searcher_vk_id == user_id,
            Candidate.favorite_status.in_([self.STATUS_VIEWED, self.STATUS_CURRENT, self.STATUS_INACTIVE])
        ).count()

    def get_blacklist_count(self, user_id: int) -> int:
        """Получить количество кандидатов в черном списке"""
        return self.session.query(Candidate).filter(
            Candidate.searcher_vk_id == user_id,
            Candidate.blacklist_status.in_([self.STATUS_VIEWED, self.STATUS_CURRENT, self.STATUS_INACTIVE])
        ).count()

    def delete_candidate_completely(self, user_id: int, candidate_vk_id: int) -> bool:
        """Полностью удалить кандидата (с фотографиями)"""
        candidate = self._get_or_create_candidate(candidate_vk_id, user_id)

        if not candidate:
            return False

        try:
            # Удаляем фото кандидата
            self.session.query(Photo).filter(
                Photo.candidates_id == candidate.candidate_id
            ).delete()

            # Удаляем кандидата
            self.session.delete(candidate)
            self.session.commit()
            return True

        except Exception as e:
            print(f"Ошибка при удалении кандидата: {e}")
            self.session.rollback()
            return False

    def get_candidates_statistics(self, user_id: int) -> dict:
        """Получить статистику кандидатов"""
        unviewed_count = self.session.query(Candidate).filter(
            Candidate.searcher_vk_id == user_id,
            Candidate.view_status == self.STATUS_NOT_VIEWED,
            Candidate.favorite_status.in_([self.STATUS_NOT_VIEWED, self.STATUS_INACTIVE]),
            Candidate.blacklist_status.in_([self.STATUS_NOT_VIEWED, self.STATUS_INACTIVE])
        ).count()

        favorites_count = self.get_favorites_count(user_id)
        blacklist_count = self.get_blacklist_count(user_id)

        return {
            'unviewed': unviewed_count,
            'favorites': favorites_count,
            'blacklist': blacklist_count
        }

    def delete_viewed_candidates(self, user_id: int) -> int:
        """Удалить просмотренных кандидатов (кроме избранных и черного списка)"""
        candidates_to_delete = self.session.query(Candidate).filter(
            Candidate.searcher_vk_id == user_id,
            Candidate.view_status == self.STATUS_VIEWED,
            Candidate.favorite_status == self.STATUS_NOT_VIEWED,
            Candidate.blacklist_status == self.STATUS_NOT_VIEWED
        ).all()

        deleted_count = 0
        if candidates_to_delete:
            for candidate in candidates_to_delete:
                # Удаляем фото кандидата
                self.session.query(Photo).filter(
                    Photo.candidates_id == candidate.candidate_id
                ).delete()
                # Удаляем кандидата
                self.session.delete(candidate)
                deleted_count += 1

            self.session.commit()

        return deleted_count

    def reset_favorites_view(self, user_id: int):
        """Сбросить статус просмотра фаворитов"""
        self.session.query(Candidate).filter(
            Candidate.searcher_vk_id == user_id,
            Candidate.favorite_status == self.STATUS_INACTIVE
        ).update({"favorite_status": self.STATUS_VIEWED})
        self.session.commit()

    def reset_blacklist_view(self, user_id: int):
        """Сбросить статус просмотра черного списка"""
        self.session.query(Candidate).filter(
            Candidate.searcher_vk_id == user_id,
            Candidate.blacklist_status == self.STATUS_INACTIVE
        ).update({"blacklist_status": self.STATUS_VIEWED})
        self.session.commit()
