import requests

from vk_bot_api.tokens import ACCESS_TOKEN_VK


def get_city_id(city_name):
    """
    Возвращает ID города и название.
    """
    ACCESS_TOKEN = ACCESS_TOKEN_VK  # Импортируйте токен вк

    url = 'https://api.vk.com/method/database.getCities'

    response = requests.get(url, params={
        'access_token': ACCESS_TOKEN,
        'v': '5.130',
        'country_id': 1,
        'q': city_name,
        'count': 1
    })

    city = response.json()['response']['items'][0]
    return city['id'], city['title']

# print(get_city_id('Москва'))
