import requests


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
