import logging
import sys
from typing import Optional

import websocket
import math
import datetime
import hashlib
import base64
import hmac
import json
import pyaudio
import wave
from urllib.parse import urlencode
import time
import ssl
from wsgiref.handlers import format_date_time
from datetime import datetime
from time import mktime
import _thread as thread
import threading
import os

# 配置日志记录
logging.getLogger().handlers = []
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', stream=sys.stdout)

# 第一帧的标识
STATUS_FIRST_FRAME = 0
# 中间帧标识
STATUS_CONTINUE_FRAME = 1
# 最后一帧的标识
STATUS_LAST_FRAME = 2

# 科大讯飞开放平台的相关信息
# https://www.xfyun.cn/doc/asr/voicedictation/API.html
APPID = '00b791b9'
API_KEY = 'eecbc528ed5007744abf3a785118cd79'
API_SECRET = 'MmIzYzc1NjU3NTdjN2RlODNmYWNkYzM1'
# 科大讯飞语音听写的 WebSocket 地址
HOST = "iat-api.xfyun.cn"


class WsParam:
    def __init__(self, app_id, api_key, api_secret, audio_file, vad_eos=1000):
        self.app_id = app_id
        self.api_key = api_key
        self.api_secret = api_secret
        self.audio_file = audio_file

        # 公共参数(common)
        self.CommonArgs = {"app_id": self.app_id}
        # 业务参数 business，更多个性化参数可在官网查看：https://www.xfyun.cn/doc/asr/voicedictation/API.html
        # vad_eos：结束录音后静音等待，单位是 ms
        self.BusinessArgs = {"domain": "iat", "language": "zh_cn", "accent": "mandarin", "vinfo": 1, "vad_eos": vad_eos}

    def create_url(self):
        url = f'wss://{HOST}/v2/iat'
        now = datetime.now()
        date = format_date_time(mktime(now.timetuple()))

        signature_origin = "host: " + HOST + "\n"
        signature_origin += "date: " + date + "\n"
        signature_origin += "GET " + "/v2/iat " + "HTTP/1.1"
        signature_sha = hmac.new(self.api_secret.encode('utf-8'), signature_origin.encode('utf-8'),
                                 digestmod=hashlib.sha256).digest()
        signature_sha = base64.b64encode(signature_sha).decode(encoding='utf-8')

        authorization_origin = "api_key=\"%s\", algorithm=\"%s\", headers=\"%s\", signature=\"%s\"" % (
            self.api_key, "hmac-sha256", "host date request-line", signature_sha)
        authorization = base64.b64encode(authorization_origin.encode('utf-8')).decode(encoding='utf-8')
        v = {
            "authorization": authorization,
            "date": date,
            "host": HOST
        }
        url = url + '?' + urlencode(v)
        return url


class ASR_Caller:
    """
    语音识别、语音合成
    """

    def __init__(self, vad_eos=1000):
        self.temp_result = []
        self.result = None
        self.audio_file_path = "output.wav"
        self.event = threading.Event()
        self.ws_param = WsParam(app_id=APPID, api_key=API_KEY, api_secret=API_SECRET, audio_file=None, vad_eos=vad_eos)
        # 每次读取的音频数据块的大小，单位是字节
        self.chunk = 1024
        self.format = pyaudio.paInt16
        self.channels = 1
        self.rate = 16000
        self.silence_threshold = 500
        self.silence_duration = int(1 * self.rate / self.chunk)

    def on_message(self, ws, message):
        try:
            code = json.loads(message)["code"]
            sid = json.loads(message)["sid"]
            if code != 0:
                err_msg = json.loads(message)["message"]
                logging.error("sid: %s, call error: %s, code is: %s" % (sid, err_msg, code))
            else:
                data = json.loads(message)["data"]["result"]["ws"]
                temp_result = ""
                for i in data:
                    for w in i["cw"]:
                        temp_result += w["w"]
                logging.info("sid: %s, call success!\ndata is: %s" % (sid, json.dumps(data, ensure_ascii=False)))
                self.temp_result.append(temp_result)
        except Exception as e:
            logging.error("receive msg, but parse exception: ", e)

    def on_error(self, ws, error):
        logging.error(f"### error: {error} ###")
        # 设置事件，表示发生错误
        self.event.set()

    def on_close(self, ws, a, b):
        logging.info("### closed ###")
        # 最终结果
        self.result = "".join(self.temp_result)
        # 设置事件，表示连接已关闭
        self.event.set()

    def on_open(self, ws):
        def run(*args):
            frame_size = 8000
            interval = 0.04
            status = STATUS_FIRST_FRAME

            with open(self.ws_param.audio_file, "rb") as fp:
                while True:
                    buf = fp.read(frame_size)
                    if not buf:
                        status = STATUS_LAST_FRAME

                    # 第一帧处理
                    # 发送第一帧音频，带 business 参数
                    # appid 必须带上，只需第一帧发送
                    # encoding = raw：原生音频（支持单声道的 pcm）
                    # encoding = speex：speex 压缩后的音频（8k）
                    # encoding = speex-wb：speex 压缩后的音频（16k）
                    # encoding = lame：mp3 格式
                    # 请注意压缩前也必须是采样率 16k 或 8k 单声道的 pcm
                    if status == STATUS_FIRST_FRAME:
                        d = {"common": self.ws_param.CommonArgs,
                             "business": self.ws_param.BusinessArgs,
                             "data": {"status": 0, "format": "audio/L16;rate=16000",
                                      "audio": str(base64.b64encode(buf), 'utf-8'),
                                      "encoding": "raw"}}
                        d = json.dumps(d)
                        ws.send(d)
                        status = STATUS_CONTINUE_FRAME
                    elif status == STATUS_CONTINUE_FRAME:
                        d = {"data": {"status": 1, "format": "audio/L16;rate=16000",
                                      "audio": str(base64.b64encode(buf), 'utf-8'),
                                      "encoding": "raw"}}
                        ws.send(json.dumps(d))
                    elif status == STATUS_LAST_FRAME:
                        d = {"data": {"status": 2, "format": "audio/L16;rate=16000",
                                      "audio": str(base64.b64encode(buf), 'utf-8'),
                                      "encoding": "raw"}}
                        ws.send(json.dumps(d))
                        time.sleep(1)
                        break
                    time.sleep(interval)
            ws.close()

        thread.start_new_thread(run, ())

    def clean_result(self):
        self.temp_result = []
        self.result = None

    def recognize_audio_file(self, audio_file_path: str = None) -> Optional[str]:
        """
        音频文件识别
        :param audio_file_path: 音频文件路径
        :return: 识别结果
        """
        audio_file_path = audio_file_path if audio_file_path is not None else self.audio_file_path
        self.ws_param.audio_file = audio_file_path
        ws_url = self.ws_param.create_url()
        websocket.enableTrace(False)
        ws = websocket.WebSocketApp(ws_url, on_open=self.on_open, on_message=self.on_message, on_error=self.on_error,
                                    on_close=self.on_close)
        ws.run_forever(sslopt={"cert_reqs": ssl.CERT_NONE})

        # 等待结果
        self.event.wait()
        return self.result

    def recognize_real_time(self, audio_file_path: str = None, silence_duration_factor: int = 1) -> Optional[str]:
        """
        实时语音识别
        :param audio_file_path: 音频文件路径
        :param silence_duration_factor: 静音持续时间的放大系数（开始前等待）
        :return:
        """
        self.clean_result()
        audio_file_path = audio_file_path if audio_file_path is not None else self.audio_file_path
        self.event.clear()

        # 根据传入的系数调整静音持续时间
        self.silence_duration = int(silence_duration_factor * self.rate / self.chunk)

        p = pyaudio.PyAudio()
        stream = p.open(format=self.format, channels=self.channels, rate=self.rate, input=True,
                        frames_per_buffer=self.chunk)
        # 存储每次读取到的音频数据块
        frames = []
        silent_frames = 0

        logging.info("===> 开始录音")

        while True:
            data = stream.read(self.chunk)
            frames.append(data)
            # 将二进制的音频数据 data 转换为整数列表 audio_data
            # 每次取两个字节的数据，'little' 表示使用小端字节序，signed=True 表示将数据解释为有符号整数
            # ange(0, len(data), 2) 表示从 0 开始，每次递增 2，直到 len(data) 结束，这样可以依次处理每两个字节的数据
            audio_data = [int.from_bytes(data[i:i + 2], 'little', signed=True) for i in range(0, len(data), 2)]
            # 计算音频数据的能量
            energy = math.sqrt(sum([x ** 2 for x in audio_data]) / len(audio_data))

            # 音频数据处于静音状态
            if energy < self.silence_threshold:
                silent_frames += 1
                if silent_frames >= self.silence_duration:
                    break
            else:
                silent_frames = 0

        logging.info("<=== 录音结束")

        stream.stop_stream()
        stream.close()
        p.terminate()

        # 在创建文件之前，确保目录存在
        audio_dir = os.path.dirname(audio_file_path)
        if not os.path.exists(audio_dir):
            os.makedirs(audio_dir)

        wf = wave.open(audio_file_path, 'wb')
        wf.setnchannels(self.channels)
        wf.setsampwidth(p.get_sample_size(self.format))
        wf.setframerate(self.rate)
        wf.writeframes(b''.join(frames))
        wf.close()

        # 调用音频文件识别函数
        self.recognize_audio_file(audio_file_path)

        # 等待结果
        self.event.wait()
        return self.result


if __name__ == "__main__":
    asr_caller = ASR_Caller()
    choice = input("请选择识别方式（1: 音频文件识别，2: 实时语音识别）：")
    if choice == '1':
        result = asr_caller.recognize_audio_file(r'../voice_output/output.wav')
        print(f"识别结果: {result}")
    elif choice == '2':
        result = asr_caller.recognize_real_time(r'../voice_output/output.wav')
        print(f"识别结果: {result}")
    else:
        print("无效的选择，请输入 1 或 2")
