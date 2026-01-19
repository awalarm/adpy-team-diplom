import requests


def search_vk_users(token, city, age_from, age_to, sex):
    """
    Возвращает список кандидатов
    """
    data = requests.get('https://api.vk.com/method/users.search', params={
        'access_token': token,
        'v': '5.199',
        'hometown': city,
        'age_from': age_from,
        'age_to': age_to,
        'sex': sex,
        'fields': 'photo_100',
        'count': 50,
        'has_photo': 1,
        'status': 1  # не женат/не замужем
    }).json()

    candidates = []
    for user in data.get('response', {}).get('items', []):
        # Только открытые профили
        if user.get('is_closed') is False:
            candidates.append({
                'id': user['id'],  # vk_user_id
                'first_name': user['first_name'],
                'last_name': user['last_name'],
                'profile_link': f"https://vk.com/id{user['id']}"
            })

    return candidates


# проверка
#
# from vk_bot_api.city_id import get_city_id
# from vk_bot_api.tokens import ACCESS_TOKEN_VK
# id_city, city = get_city_id('Москва')
# print(search_vk_users(ACCESS_TOKEN_VK, id_city, 28,28,2))

def get_candidate_photos(token, user_id):
    """
    Получает 3 самые популярные фото кандидата из ВСЕХ фото.
    """
    data = requests.get('https://api.vk.com/method/photos.getAll', params={
        'access_token': token,
        'v': '5.199',
        'owner_id': user_id,
        'count': 100,  # Берем больше фото для выбора
        'extended': 1,  # Получаем информацию о лайках
        'no_service_albums': 0  # Включаем все альбомы
    }).json()

    photos = []
    if 'response' in data:
        # Сортируем фото по количеству лайков (по убыванию)
        sorted_photos = sorted(data['response']['items'],
                               key=lambda x: x.get('likes', {}).get('count',
                                                                    0),
                               reverse=True)

        for photo in sorted_photos[:3]:  # Берем 3 самые популярные
            largest = max(photo['sizes'], key=lambda x: x['width'])

            photos.append({
                'vk_photo_id': photo['id'],
                'photo_link': largest['url'],
                'owner_id': user_id,
                'likes': photo.get('likes', {}).get('count', 0)
            })

    return photos
# from vk_bot_api.tokens import ACCESS_TOKEN_VK
# print(get_candidate_photos(ACCESS_TOKEN_VK, 201922956))
