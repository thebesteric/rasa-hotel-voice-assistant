# This files contains your custom actions which can be used to run
# custom Python code.
#
# See this guide on how to implement these action:
# https://rasa.com/docs/rasa/custom-actions
# This is a simple example for a custom action which utters "Hello World!"

from typing import Any, Text, Dict, List
from rasa_sdk.types import DomainDict
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from .slots import read_slots_from_domain
import logging
import sys
import os
import json

# 获取当前脚本所在的目录
current_dir = os.path.dirname(os.path.abspath(__file__))
# 构建目录路径
rasa_utils_dir = os.path.abspath(os.path.join(current_dir, '../../utils'))
print(rasa_utils_dir)
# 将目录添加到系统路径中
sys.path.append(rasa_utils_dir)

# 导入 helper.py 文件中的内容
try:
    from rasa_helper import Rasa_Helper
    from thread_local_utils import Thread_Local_Utils
    from llm_caller import LLM_Caller
    from llm_prompter import LLM_Prompter
except ImportError as e:
    print(f"导入失败：{e}，无法导入 {rasa_utils_dir} 文件，请检查文件路径和内容。")

# 配置日志记录
logging.getLogger().handlers = []
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', stream=sys.stdout)

# 获取实体相关的意图
ENTITY_INTENTS = read_slots_from_domain()


class ActionInterruptProcess(Action):
    def name(self):
        return "action_interrupt_process"

    def run(self, dispatcher, tracker, domain):
        logging.info(f"==> [{self.name()}] 流程已中断")
        return Rasa_Helper.restart_process(dispatcher, tracker)


class ActionNluFallback(Action):
    def name(self) -> str:
        return "action_nlu_fallback"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: DomainDict) -> List[Dict[Text, Any]]:
        latest_message = tracker.latest_message.get('text')
        logging.info(f"==> [{self.name()}] 语义理解失败：{latest_message}")
        dispatcher.utter_message(response="utter_nlu_fallback")
        return Rasa_Helper.restart_process(dispatcher, tracker)


class ActionMessageListener(Action):
    def name(self) -> Text:
        return "action_message_listener"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: DomainDict) -> List[Dict[Text, Any]]:
        # 获取当前用户
        sender_id = Rasa_Helper.get_sender_id(tracker)
        # 获取用户的最新消息
        latest_message = tracker.latest_message.get('text')
        # 获取用户的意图
        intent = Rasa_Helper.get_intent(tracker)
        # 获取当前需求槽位
        cur_required_intent = Rasa_Helper.get_cur_required_intent(tracker)
        # 获取当前需求槽位
        cur_required_slot = Rasa_Helper.get_cur_required_slot(tracker)
        # 是否在循环中
        action_in_loop = Rasa_Helper.get_action_in_loop(tracker)

        logging.info(
            f"[{self.name()}] 用户：{sender_id}，意图：{intent}，需求意图：{cur_required_intent}，需求槽位：{cur_required_slot}，循环中：{action_in_loop}，监听消息：{latest_message}")

        # 对未打扫进行特殊处理（多轮 action_in_loop 对话时需要使用）
        if intent == "room_un_clean" or cur_required_intent == "room_un_clean":
            # 发送一个意图来触发指定的 action
            logging.info(f"[{self.name()}] 发送到指定行为：action_room_un_clean")
            return Rasa_Helper.action_followup("action_room_un_clean")

        # 处理 room_cleaned 意图
        if intent == "room_cleaned":
            logging.info(f"[{self.name()}] 发送到指定行为：action_room_cleaned")
            return Rasa_Helper.action_followup("action_room_cleaned")

        # 处理 room_exchange 意图
        if intent == "room_exchange":
            logging.info(f"[{self.name()}] 发送到指定行为：action_room_exchange")
            return Rasa_Helper.action_followup("action_room_exchange")

        return []


class ActionGreeting(Action):
    def name(self) -> str:
        return "action_greeting"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: DomainDict) -> List[Dict[Text, Any]]:
        Rasa_Helper.say_and_send_message(dispatcher, "你好呀，有什么需要我帮忙的吗？")
        return []


class ActionRoomUnClean(Action):
    def name(self) -> str:
        return "action_room_un_clean"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: DomainDict) -> List[Dict[Text, Any]]:

        intent = Rasa_Helper.get_intent(tracker)
        action_in_loop = Rasa_Helper.get_action_in_loop(tracker)
        room_no = Rasa_Helper.get_room_no(tracker)
        remind_time = Rasa_Helper.get_slot(tracker, "room_un_clean_remind_time")
        remind_time_unit = Rasa_Helper.get_slot(tracker, "room_un_clean_remind_time_unit")
        # 获取当前必须的槽位列表
        require_slots = Rasa_Helper.get_required_slots(intent, ENTITY_INTENTS)

        # 日志打印
        logging.info(
            f"[{self.name()}] RASA parse slots: intent = {intent}，room_no = {room_no}, remind_time = {remind_time}, remind_time_unit = {remind_time_unit}, action_in_loop = {action_in_loop}")

        # 中断流程
        if intent == "interrupt_process":
            logging.info(f"[{self.name()}] 已中断")
            return Rasa_Helper.restart_process(dispatcher, tracker)

        # 修正 intent 错误问题
        # 多轮 action_in_loop 对话的时候，当用户输入房号的时候，可能会解析成其他意图，如：room_exchange
        if intent != "room_un_clean" and action_in_loop is True:
            err_intent = intent;
            intent = "room_un_clean"
            logging.info(f"[{self.name()}] 将意图 {err_intent}，修正意图为：{intent}")

        # # 调用 LLM 进行槽位提取
        # if room_no is None or remind_time is None or remind_time_unit is None:
        #     latest_message = get_latest_message(tracker)
        #     message_with_prompt = LLM_Prompter.room_un_clean_slots_prompt(message=latest_message)
        #     llm_response = LLM_Caller.send_chat_request(slug="test", session_id=get_sender_id(tracker), message=message_with_prompt)
        #     content = llm_response.result['content']
        #     logging.info(f"[{self.name()}] LLM 响应：{content}")
        #     exception = content['exception']
        #     if exception is None and llm_response.result['type'] == "json":
        #         room_no = content['room_un_clean_room_no']
        #         remind_time = content['room_un_clean_remind_time']
        #         remind_time_unit = content['room_un_clean_remind_time_unit']
        #
        #     # 日志打印
        #     logging.info(
        #         f"[{self.name()}] LLM parse slots: room_no = {room_no}, remind_time = {remind_time}, remind_time_unit = {remind_time_unit}")

        # 打扫计划取消
        if intent == "room_un_clean_cancel" and action_in_loop:
            # todo 删除未打扫的房间记录
            message = "好的，已取消打扫计划" if room_no is None else f"好的，已取消 {room_no} 房间的打扫计划"
            Rasa_Helper.say_and_send_message(dispatcher, message)
            return Rasa_Helper.restart_process(dispatcher, tracker)

        # 未指定房间号的情况
        if room_no is None:
            Rasa_Helper.say_and_send_message(dispatcher, "您需要打扫哪间房？可以说：8001 房间")
            cur_required_intent = Rasa_Helper.set_cur_required_intent(intent)
            cur_required_slot = Rasa_Helper.set_cur_required_slot("room_un_clean_room_no")
            return [cur_required_intent,
                    cur_required_slot,
                    Rasa_Helper.slot_set("room_un_clean_room_no", None),
                    Rasa_Helper.slot_set("room_un_clean_remind_time", remind_time),
                    Rasa_Helper.slot_set("room_un_clean_remind_time_unit", remind_time_unit),
                    *Rasa_Helper.action_loop(self.name())]

        # 所有必填项都已经填充
        if all(tracker.slots.get(slot) for slot in require_slots) or room_no is not None:
            if remind_time and remind_time_unit:
                # todo 记录未打扫的房间，并记录提醒信息
                Rasa_Helper.say_and_send_message(dispatcher,
                                                 f"好的，{remind_time} {remind_time_unit}后，我会提醒您打扫 {room_no} 房间")
            else:
                # todo 记录未打扫的房间
                Rasa_Helper.say_and_send_message(dispatcher, f"好的，我记住了，{room_no} 房间未打扫")

        return Rasa_Helper.restart_process(dispatcher, tracker)


class ActionRoomUnCleanCancel(Action):
    def name(self) -> str:
        return "action_room_un_clean_cancel"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: DomainDict) -> List[Dict[Text, Any]]:
        intent = Rasa_Helper.get_intent(tracker)
        room_no = Rasa_Helper.get_room_no(tracker)
        action_in_loop = Rasa_Helper.get_action_in_loop(tracker)
        # 日志打印
        logging.info(
            f"[{self.name()}] RASA parse slots: intent = {intent}，room_no = {room_no}, action_in_loop = {action_in_loop}")

        # 流程中断
        if intent == "interrupt_process":
            logging.info(f"[{self.name()}] 已中断")
            return Rasa_Helper.restart_process(dispatcher, tracker)

        if room_no is None:
            Rasa_Helper.say_and_send_message(dispatcher, "您需要取消哪间房间的打扫？可以说：取消打扫 8001 房间")
            cur_required_intent = Rasa_Helper.set_cur_required_intent(intent)
            cur_required_slot = Rasa_Helper.set_cur_required_slot("room_un_clean_room_no")
            return [cur_required_intent,
                    cur_required_slot,
                    Rasa_Helper.slot_set("room_un_clean_room_no", None),
                    *Rasa_Helper.action_loop(self.name())]
        else:
            # todo 删除未打扫的房间记录
            Rasa_Helper.say_and_send_message(dispatcher, f"好的，已为您取消 {room_no} 房间的打扫计划")

        return Rasa_Helper.restart_process(dispatcher, tracker)


class ActionRoomCleaned(Action):
    def name(self) -> str:
        return "action_room_cleaned"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: DomainDict) -> List[Dict[Text, Any]]:
        intent = Rasa_Helper.get_intent(tracker)
        room_no = Rasa_Helper.get_slot(tracker, "room_cleaned_room_no")

        # 日志打印
        logging.info(f"[{self.name()}] RASA parse slots: room_no = {room_no}")

        # 中断流程
        if intent == "interrupt_process":
            logging.info(f"[{self.name()}] 已中断")
            return Rasa_Helper.restart_process(dispatcher, tracker)

        # 获取当前必须的槽位列表
        print("intent ====================", intent)
        print("ENTITY_INTENTS ====================", ENTITY_INTENTS)
        require_slots = Rasa_Helper.get_required_slots(intent, ENTITY_INTENTS)
        print("====================", require_slots)

        # 所有必填项都已经填充
        if all(tracker.slots.get(slot) for slot in require_slots):
            # todo 删除未打扫的房间记录
            Rasa_Helper.say_and_send_message(dispatcher, f"好的，知道啦，{room_no} 房间已经打扫干净")

        return Rasa_Helper.restart_process(dispatcher, tracker)


class ActionRoomExchange(Action):
    def name(self) -> str:
        return "action_room_exchange"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: DomainDict) -> List[Dict[Text, Any]]:
        intent = Rasa_Helper.get_intent(tracker)
        from_room_no = Rasa_Helper.get_slot(tracker, "room_exchange_from_room_no")
        to_room_no = Rasa_Helper.get_slot(tracker, "room_exchange_to_room_no")
        # 是否在循环中
        action_in_loop = Rasa_Helper.get_action_in_loop(tracker)

        # 日志打印
        logging.info(f"[{self.name()}] RASA parse slots: from_room_no = {from_room_no}, to_room_no = {to_room_no}")

        # 中断流程
        if intent == "interrupt_process":
            logging.info(f"[{self.name()}] 已中断")
            return Rasa_Helper.restart_process(dispatcher, tracker)

        # 尝试从线程本地变量中获取 from_room_no
        thread_local_from_room_no_key = "thread_local_from_room_no"
        thread_local_from_room_no = Thread_Local_Utils.get_variable(thread_local_from_room_no_key)
        if action_in_loop and thread_local_from_room_no is not None and from_room_no is not None and to_room_no is None:
            # 从线程中取出 thread_local_from_room_no，并完成交换
            temp = thread_local_from_room_no
            to_room_no = from_room_no
            from_room_no = temp
            # 日志打印
            logging.info(f"[{self.name()}] ThreadLocal parse: from_room_no = {from_room_no}, to_room_no = {to_room_no}")

        # 尝试从线程本地变量中获取 to_room_no
        thread_local_to_room_no_key = "thread_local_to_room_no"
        thread_local_to_room_no = Thread_Local_Utils.get_variable(thread_local_to_room_no_key)
        if action_in_loop and thread_local_to_room_no is not None and from_room_no is None and to_room_no is not None:
            # 从线程中取出 thread_local_to_room_no，并完成交换
            temp = thread_local_to_room_no
            from_room_no = to_room_no
            to_room_no = temp
            # 日志打印
            logging.info(f"[{self.name()}] ThreadLocal parse: from_room_no = {from_room_no}, to_room_no = {to_room_no}")

        # 未指定任何房间号的情况
        if from_room_no is None and to_room_no is None:
            Rasa_Helper.say_and_send_message(dispatcher, "您需调整哪一间房间？可以说：将 8001 房间调整到 8002 房间")
            cur_required_intent = Rasa_Helper.set_cur_required_intent(intent)
            cur_required_slot = Rasa_Helper.set_cur_required_slot("room_exchange_from_room_no")
            return [cur_required_intent,
                    cur_required_slot,
                    Rasa_Helper.slot_set("room_exchange_from_room_no", None),
                    Rasa_Helper.slot_set("room_exchange_to_room_no", None),
                    *Rasa_Helper.action_loop(self.name())]

        # 仅指定了调整前房间号的情况
        if from_room_no is None and to_room_no is not None:
            Rasa_Helper.say_and_send_message(dispatcher, f"您需要调整哪一间房到 {to_room_no}？可以说：调整 8001 房间")

            # 如果在循环中，且 to_room_no 不为 None，from_room_no 为 None，则将 to_room_no 存储到线程本地变量中
            # 应对多轮 action_in_loop 对话中，要求用户输入 from_room_no 的时候，用户直接输入房间号，导致 RASA 将 from_room_no 解析为 to_room_no 的情况
            if action_in_loop:
                # 将 to_room_no 存储到线程本地变量中
                Thread_Local_Utils.set_variable(thread_local_to_room_no_key, to_room_no)
                # 日志打印
                logging.info(f"[{self.name()}] ThreadLocal set: to_room_no = {to_room_no}")

            cur_required_intent = Rasa_Helper.set_cur_required_intent(intent)
            cur_required_slot = Rasa_Helper.set_cur_required_slot("room_exchange_from_room_no")
            return [cur_required_intent,
                    cur_required_slot,
                    Rasa_Helper.slot_set("room_exchange_from_room_no", None),
                    Rasa_Helper.slot_set("room_exchange_to_room_no", to_room_no),
                    *Rasa_Helper.action_loop(self.name())]

        # 仅指定了调整后房间号的情况
        if from_room_no is not None and to_room_no is None:
            Rasa_Helper.say_and_send_message(dispatcher,
                                             f"您需要将 {from_room_no} 调整到哪一间房？可以说：调整到 8001 房间")

            # 如果在循环中，且 from_room_no 不为 None，to_room_no 为 None，则将 from_room_no 存储到线程本地变量中
            # 应对多轮 action_in_loop 对话中，要求用户输入 to_room_no 的时候，用户直接输入房间号，导致 RASA 将 to_room_no 解析为 from_room_no 的情况
            if action_in_loop:
                # 将 from_room_no 存储到线程本地变量中
                Thread_Local_Utils.set_variable(thread_local_from_room_no_key, from_room_no)
                # 日志打印
                logging.info(f"[{self.name()}] ThreadLocal set: from_room_no = {from_room_no}")

            cur_required_intent = Rasa_Helper.set_cur_required_intent(intent)
            cur_required_slot = Rasa_Helper.set_cur_required_slot("room_exchange_to_room_no")
            return [cur_required_intent,
                    cur_required_slot,
                    Rasa_Helper.slot_set("room_exchange_from_room_no", from_room_no),
                    Rasa_Helper.slot_set("room_exchange_to_room_no", None),
                    *Rasa_Helper.action_loop(self.name())]

        # 获取当前必须的槽位列表
        require_slots = Rasa_Helper.get_required_slots(intent, ENTITY_INTENTS)

        # 所有必填项都已经填充
        if all(tracker.slots.get(slot) for slot in require_slots) or (
                from_room_no is not None and to_room_no is not None):
            # todo 调整房间（查看房型，计算价格，如果价格不同，提示用户）
            Rasa_Helper.say_and_send_message(dispatcher, f"好的，收到，已将 {from_room_no} 房间调整到 {to_room_no} 房间")

        # 清理线程存储变量
        Thread_Local_Utils.clear_variables()
        return Rasa_Helper.restart_process(dispatcher, tracker)


class ActionRoomReplenishment(Action):
    def name(self) -> Text:
        return "action_room_replenishment"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: DomainDict) -> List[Dict[Text, Any]]:
        # 获取用户输入房间号
        room_no = tracker.get_slot("room_replenishment_room_no")
        # 获取用户输入的实体
        entities = tracker.latest_message.get("entities", [])
        # 日志打印
        logging.info(f"[{self.name()}] filter before: room_no: {room_no}, entities: {entities}")

        # 调用 LLM 解析槽位
        latest_message = Rasa_Helper.get_latest_message(tracker)
        message_with_prompt = LLM_Prompter.room_replenishment_prompt(user_input=latest_message)
        llm_response = LLM_Caller.send_chat_request(slug="test", session_id=Rasa_Helper.get_sender_id(tracker), user_input=message_with_prompt)
        room_items = llm_response.result['content']

        if not isinstance(room_items, dict):
            room_items = json.loads(room_items)

        # 解析成文本响应
        # room_no = room_items["room_no"]
        item_strs = []
        for item in room_items["items"]:
            item_str = f"{item['name']} {item['quantity']} {item['unit']}"
            item_strs.append(item_str)
        items_str = ", ".join(item_strs)
        response = f"{room_no} 房间补货：{items_str}"

        # 响应用户
        Rasa_Helper.say_and_send_message(dispatcher, f"好的，收到，{response}")

        # 将提取的数据存储到槽位中
        # return [Rasa_Helper.slot_set("room_items", room_items)]
        return []