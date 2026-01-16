import requests


def search_vk_users(token, city_id, age_from, age_to, sex):
    """
    Возвращает список кандидатов
    """
    data = requests.get('https://api.vk.com/method/users.search', params={
        'access_token': token,
        'v': '5.199',
        'city': city_id,
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
        if user.get('is_closed') == False:
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
