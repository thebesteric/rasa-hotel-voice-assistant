from typing import Any, Text, Dict, List, Optional
from rasa_sdk.types import DomainDict
from rasa_sdk.events import AllSlotsReset, Restarted, SlotSet, UserUtteranceReverted, FollowupAction, ActiveLoop, \
    ActionExecutionRejected
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from llm_prompter import LLM_Prompter
from llm_caller import LLM_Caller
from tts_speaker import TTS_Speaker
import logging
import inspect


class Rasa_Helper:
    def __init__(self):
        pass

    @staticmethod
    def action_loop(action_name: str) -> list[ActiveLoop]:
        return [ActiveLoop(action_name), Rasa_Helper.set_action_in_loop(True)]

    @staticmethod
    def action_followup(action_name: str) -> list[FollowupAction]:
        return [FollowupAction(action_name)]

    @staticmethod
    def action_cancel_loop(action_name: str) -> ActiveLoop:
        return ActiveLoop(None)

    @staticmethod
    def action_execution_rejected(action_name: str) -> ActionExecutionRejected:
        return ActionExecutionRejected(action_name)

    @staticmethod
    def slot_set(slot_name: str, slot_value: str) -> SlotSet:
        return SlotSet(slot_name, slot_value)

    @staticmethod
    def get_current_function_name():
        # 获取当前栈帧
        current_frame = inspect.currentframe()
        # 获取调用当前函数的栈帧
        calling_frame = inspect.getouterframes(current_frame, 2)
        # 从栈帧信息中获取函数名
        function_name = calling_frame[1][3]
        return function_name

    @staticmethod
    def get_intent(tracker: Tracker) -> Optional[str]:
        intent = tracker.latest_message.get('intent')
        if intent:
            return intent.get('name')
        else:
            logging.warning(f"{Rasa_Helper.get_current_function_name()} 未获取到用户意图")
            return None

    @staticmethod
    def get_slot(tracker: Tracker, slot_name: str):
        slots = tracker.slots
        return slots.get(slot_name)

    @staticmethod
    def get_latest_message(tracker: Tracker):
        return tracker.latest_message.get('text')

    @staticmethod
    def get_sender_id(tracker: Tracker):
        return str(tracker.sender_id)

    @staticmethod
    def get_cur_required_slot(tracker: Tracker) -> Optional[str]:
        return str(tracker.get_slot("cur_required_slot"))

    @staticmethod
    def set_cur_required_slot(slot_value: str) -> SlotSet:
        return SlotSet("cur_required_slot", slot_value)

    @staticmethod
    def get_cur_required_intent(tracker: Tracker) -> Optional[str]:
        return str(tracker.get_slot("cur_required_intent"))

    @staticmethod
    def set_cur_required_intent(intent_value: str) -> SlotSet:
        return SlotSet("cur_required_intent", intent_value)

    @staticmethod
    def set_action_in_loop(is_in_loop: bool) -> SlotSet:
        return SlotSet("action_in_loop", is_in_loop)

    @staticmethod
    def get_action_in_loop(tracker: Tracker) -> bool:
        return False if tracker.get_slot("action_in_loop") is None else bool(tracker.get_slot("action_in_loop"))

    @staticmethod
    def restart_process(dispatcher: CollectingDispatcher, tracker: Tracker) -> List[Dict[Text, Any]]:
        print(f"==> [{Rasa_Helper.get_current_function_name()}] 重启流程")

        # 发送扩展后的响应
        # json_message 格式是给 http://localhost:5005/webhooks/rest/webhook 的响应添加 custom 的 key 使用
        extended_response = {
            "restart_process": True,
            "intent": Rasa_Helper.get_intent(tracker),
            "slots": dict(tracker.slots),
        }
        dispatcher.utter_message(json_message=extended_response)

        # 清空槽位、事件列表
        # AllSlotsReset() 重置所有槽位的值，将对话状态恢复到初始状态
        # Restarted() 不仅会重置所有槽位的值，还会清除对话历史记录，将对话状态恢复到初始状态
        return [Restarted(), ActiveLoop(None)]

    @staticmethod
    def say_and_send_message(dispatcher: CollectingDispatcher, message: str):
        # 发送消息
        dispatcher.utter_message(text=message)
        # 语音合成
        # TTS_Speaker.say(text=message)

    @staticmethod
    def get_required_slots(intent: str, entity_intents: dict) -> List[str]:
        entity_intent = entity_intents.get(intent)
        return entity_intent.slots.get("require_slots")

    @staticmethod
    def get_room_no(tracker: Tracker):
        # 兜底，尝试获取房间号，单纯输get_room_no入房间号会触发其他意图的槽位
        room_no_slots = ["room_un_clean_room_no", "room_cleaned_room_no", "room_exchange_from_room_no",
                         "room_exchange_to_room_no"]
        for room_no_slot in room_no_slots:
            room_no = Rasa_Helper.get_slot(tracker, room_no_slot)
            if room_no is not None:
                return room_no
        return None
