import json
import os, sys

current_dir = os.path.dirname(os.path.abspath(__file__))
rasa_utils_dir = os.path.abspath(os.path.join(current_dir, '../utils'))
sys.path.append(rasa_utils_dir)

# 导入 helper.py 文件中的内容
try:
    from rasa_caller import Rasa_Caller
except ImportError:
    print(f"无法导入 {rasa_utils_dir} 文件，请检查文件路径和内容。")


# Rasa 服务器地址
# 启动命令：rasa run --enable-api --cors "*" --debug
rasa_server_url = 'http://localhost:5005/webhooks/rest/webhook'

if __name__ == '__main__':
    while True:
        # 监听用户输入
        user_input = input("请输入你的消息（输入 '/bye' 结束程序）：")
        if user_input.lower() == '/bye':
            break

        dialogs = Rasa_Caller.send("send_1", user_input)
        # 将 dialogs 转换为 JSON 格式的字符串
        dialogs_json = json.dumps([dialog.to_dict() for dialog in dialogs], ensure_ascii=False, indent=4)
        print(dialogs_json)

