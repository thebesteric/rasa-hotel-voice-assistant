import logging
from typing import Optional

import requests
import json
import time
import threading
from enum import Enum
import sys
import re

from tensorboard.plugins.debugger_v2.debug_data_provider import source_file_list_run_tag_filter

HOST = "http://localhost:3001"
API_KEY = "7RQ11EA-KJE42KB-M0EEJZZ-443YRDT"


class Attachment:
    """
    "name": "image.png",
    "mime": "image/png",
    "contentString": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAA..."
    """

    def __init__(self, name, mime, content_string):
        self.name = name
        self.mime = mime
        self.contentString = content_string


class Mode(Enum):
    CHAT = "chat"
    QUERY = "query"


class ResultResponse:
    def __init__(self, content, type):
        self.content = content
        self.type = type

    def to_dict(self):
        return {
            "content": self.content,
            "type": self.type
        }


class ChatResponse:
    """
    封装 send_chat_request 返回的响应
    """

    def __init__(self, response_data):
        # 原始响应数据
        self.data = response_data
        # 响应的 id
        self.id = response_data.get("id")
        # 响应的类型
        self.type = response_data.get("type")
        # 是否关闭
        self.close = response_data.get("close")
        # 错误信息
        self.error = response_data.get("error")
        # 聊天 id
        self.chatId = response_data.get("chatId")
        # 文本响应
        self.textResponse = response_data.get("textResponse")
        # 来源列表
        self.sources = response_data.get("sources")
        # 指标信息
        self.metrics = response_data.get("metrics")

        # 提取 thinkResponse 和 result
        if self.textResponse:
            # 提取<think>开头到</think>结尾的中间部分
            start_index = self.textResponse.find("<think>")
            end_index = self.textResponse.find("</think>")
            if start_index != -1 and end_index != -1:
                think_response = self.textResponse[start_index + len("<think>"):end_index]
                # 去除首尾的换行符
                self.thinkResponse = think_response.strip()
                # 提取 <think> 标签结束的后面所有信息
                result_response = self.textResponse[end_index + len("</think>"):].strip()
            else:
                self.thinkResponse = ""
                result_response = self.textResponse.strip()
                # 去掉可能残留的 </think> 标签
                result_response = result_response.replace("</think>", "").strip()
            # 根据类型转化
            self.result = self._convert_result_response(result_response).to_dict()
        else:
            self.thinkResponse = ""
            self.result = ResultResponse("", "text").to_dict()

    @staticmethod
    def _convert_result_response(result_response: str) -> Optional[ResultResponse]:
        """将 resultResponse 中的 ```json 代码块转换为 JSON 对象"""
        if '```json' in result_response:
            # 提取 JSON 字符串部分
            json_str = re.search(r'```json\n(.*?)```', result_response, re.DOTALL).group(1)
            try:
                return ResultResponse(json.loads(json_str), "json")
            except json.JSONDecodeError as e:
                logging.error(f"JSON 解析错误: {e}")
                return ResultResponse(result_response, "json")
        else:
            return ResultResponse(result_response, "text")

    def to_dict(self):
        """将 ChatResponse 对象转换为字典"""
        return {
            # "data": self.data,
            "id": self.id,
            "type": self.type,
            "close": self.close,
            "error": self.error,
            "chatId": self.chatId,
            "textResponse": self.textResponse,
            "sources": self.sources,
            "metrics": self.metrics,
            "thinkResponse": self.thinkResponse,
            "result": self.result
        }


class LLM_Caller:

    @staticmethod
    def send_chat_request(slug: str, session_id: str, user_input: str, mode=Mode.CHAT, attachments=None) -> Optional[ChatResponse]:
        # 请求的 URL
        url = f'{HOST}/api/v1/workspace/{slug}/chat'

        # 请求头
        headers = {
            'accept': 'application/json',
            'Authorization': f'Bearer {API_KEY}',
            'Content-Type': 'application/json'
        }

        # 请求体数据
        request_data = {
            "message": user_input,
            "mode": mode.value,
            "sessionId": session_id,
            "attachments": [] if attachments is None else attachments
        }

        # 将数据转换为 JSON 格式的字符串
        json_request_data = json.dumps(request_data)

        # 记录请求开始时间
        start_time = time.time()

        try:
            logging.info(f"正在发送请求: {url}")
            # 发送 POST 请求
            response = requests.post(url, headers=headers, data=json_request_data)
            # 停止计时线程
            elapsed_time = time.time() - start_time  # 计算总执行时间（秒）
            logging.info(f"已执行时间: {elapsed_time:.2f} 秒")

            if response.status_code == 200:
                # 将响应的 JSON 数据解析并封装到 ChatResponse 类中
                chat_response = ChatResponse(response.json())
                # 将请求调用时间添加到 ChatResponse 对象中
                chat_response.request_time = elapsed_time
                return chat_response
            else:
                logging.error(f"Request failed with status code: {response.status_code}, result: {response.json()}")
                return None
        except requests.RequestException as e:
            # 停止计时线程
            elapsed_time = time.time() - start_time  # 计算总执行时间（秒）
            logging.info(f"已执行时间: {elapsed_time:.2f} 秒")
            logging.error(f"An error occurred: {e}")
            return None


# 调用函数
if __name__ == "__main__":
    from llm_prompter import LLM_Prompter
    message = LLM_Prompter.room_un_clean_slots_prompt(user_input="一刻钟后提醒我打扫8008房间")
    start_time = time.time()
    response = LLM_Caller.send_chat_request(slug="test", session_id="sender_1", user_input=message)
    print(f"已执行时间: {time.time() - start_time:.2f} 秒")
    if response:
        print(json.dumps(response.to_dict(), indent=4, ensure_ascii=False))
