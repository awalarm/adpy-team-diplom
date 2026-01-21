from vk_api import vk_api

from config import token_vk


def write_msg(user_id, message, keyboard=None, attachment=None):
    """метод отправляет сообщение пользователю ВКонтакте через VK API"""
    local_vk_session = vk_api.VkApi(token=token_vk)
    local_vk = local_vk_session.get_api()

    params = {
        "user_id": user_id,
        "message": message,
        "random_id": randrange(10 ** 7),
    }
    if keyboard:
        params["keyboard"] = keyboard
    if attachment:
        params["attachment"] = attachment

    local_vk.messages.send(**params)