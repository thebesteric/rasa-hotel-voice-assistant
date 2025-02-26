import logging

import requests
import json

rasa_server_url = 'http://localhost:5005/webhooks/rest/webhook'


class Dialog:
    def __init__(self, recipient_id, text: str = None, custom: dict = None):
        self.recipient_id = recipient_id
        self.text = text
        self.custom = custom

    def __repr__(self):
        return f"Dialog(recipient_id='{self.recipient_id}', text='{self.text}', custom={self.custom})"

    def to_dict(self):
        return {
            "recipient_id": self.recipient_id,
            "text": self.text,
            "custom": self.custom
        }

    @staticmethod
    def get_text_dialogs(dialog_list) -> list['Dialog']:
        """
        获取所有包含 "text" 字段的 dialog
        :param dialog_list: 对话列表
        :return: 包含 "text" 字段的 dialog 列表
        """
        return [dialog for dialog in dialog_list if dialog.text is not None]

    @staticmethod
    def get_custom_dialogs(dialog_list) -> list['Dialog']:
        """
        获取所有包含 "custom" 字段的 dialog
        :param dialog_list: 对话列表
        :return: 包含 "custom" 字段的 dialog 列表
        """
        return [dialog for dialog in dialog_list if dialog.custom is not None]

    @staticmethod
    def get_custom_dialogs_with_restart_process_true(dialog_list) -> list['Dialog']:
        """
        从对话列表中获取 custom.restart_process 为 True 的 dialog
        :param dialog_list: 对话列表
        :return: custom.restart_process 为 True 的 dialog 列表
        """
        result = []
        custom_dialogs = Dialog.get_custom_dialogs(dialog_list)
        if not custom_dialogs:
            return result
        # 遍历对话列表，获取 custom.restart_process 为 True 的对话
        for custom_dialog in custom_dialogs:
            restart_process_value = custom_dialog.custom.get('restart_process')
            if restart_process_value:
                result.append(custom_dialog)
        return result


class Rasa_Caller:
    @staticmethod
    def send(sender: str, message: str) -> list[Dialog]:
        try:
            # 发送请求
            response = requests.post(rasa_server_url, json={
                "sender": sender,
                "message": message
            })
            # 检查响应状态码
            if response.status_code == 200:
                # 从响应中获取 JSON 数据
                json_data = response.json()
                json_str = json.dumps(json_data, ensure_ascii=False, indent=4)
                """
                [
                    {
                        "recipient_id": "sender_1",
                        "text": "好的，我记住了，801 房间未打扫"
                    },
                    {
                        "recipient_id": "sender_1",
                        "custom": {
                            "restart_process": Ture,
                            "intent": "room_un_clean",
                            "slots": {...}
                        }
                    }
                ]
                """
                data = json.loads(json_str)
                # 创建 Dialog 对象列表
                dialogs = []
                for item in data:
                    recipient_id = item["recipient_id"]
                    text = item["text"] if "text" in item else None
                    custom = item["custom"] if "custom" in item else None
                    dialog = Dialog(recipient_id, text, custom)
                    dialogs.append(dialog)
                return dialogs
            else:
                logging.error(f"请求失败，状态码: {response.status_code}")
        except requests.RequestException as e:
            logging.error(f"请求发生错误: {e}")

        return []
