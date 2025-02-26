import yaml

DOMAIN_FILE_PATH = '/Users/wangweijun/PycharmProjects/rasa-hotel-voice-assistant/rasa/domain.yml'


class Intent:
    def __init__(self):
        self.slots = {
            "require_slots": [],
            "optional_slots": []
        }


def read_slots_from_domain() -> dict[str, Intent]:
    intents = {}
    try:
        with open(DOMAIN_FILE_PATH, 'r', encoding='utf-8') as file:
            # 解析 yaml 文件
            data = yaml.safe_load(file)

            # 处理 intent
            if 'intents' in data:
                for intent_name in data['intents']:
                    intents[intent_name] = Intent()

            # 处理 slots
            if 'slots' in data:
                for slot_name, slot_info in data['slots'].items():
                    for intent_name in intents:
                        if slot_name.startswith(intent_name):
                            if 'influence_conversation' in slot_info:
                                if slot_info['influence_conversation']:
                                    intents[intent_name].slots['require_slots'].append(slot_name)
                                else:
                                    intents[intent_name].slots['optional_slots'].append(slot_name)

    except FileNotFoundError:
        print(f"{DOMAIN_FILE_PATH} 文件未找到")
    except yaml.YAMLError as e:
        print(f"{DOMAIN_FILE_PATH} 解析错误: {e}")

    return intents


if __name__ == '__main__':
    # 调用函数并打印结果
    result = read_slots_from_domain()
    for intent_name, slot in result.items():
        print(f"intent_name: {intent_name}")
        print(f"require_slots: {slot.slots['require_slots']}")
        print(f"optional_slots: {slot.slots['optional_slots']}")
        print()

    # 获取指定意图的槽位信息
    intent = result.get('room_un_clean')
    print(intent.slots.get('require_slots'))
    print(intent.slots.get('optional_slots'))
