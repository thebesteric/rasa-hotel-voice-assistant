# -*- coding:utf-8 -*-
#
#   author: iflytek
#
#  本demo测试时运行的环境为：Windows + Python3.7
#  本demo测试成功运行时所安装的第三方库及其版本如下，您可自行逐一或者复制到一个新的txt文件利用pip一次性安装：
#   cffi==1.12.3
#   gevent==1.4.0
#   greenlet==0.4.15
#   pycparser==2.19
#   six==1.12.0
#   websocket==0.2.1
#   websocket-client==0.56.0
#
#  语音听写流式 WebAPI 接口调用示例 接口文档（必看）：https://doc.xfyun.cn/rest_api/语音听写（流式版）.html
#  webapi 听写服务参考帖子（必看）：http://bbs.xfyun.cn/forum.php?mod=viewthread&tid=38947&extra=
#  语音听写流式WebAPI 服务，热词使用方式：登陆开放平台https://www.xfyun.cn/后，找到控制台--我的应用---语音听写（流式）---服务管理--个性化热词，
#  设置热词
#  注意：热词只能在识别的时候会增加热词的识别权重，需要注意的是增加相应词条的识别率，但并不是绝对的，具体效果以您测试为准。
#  语音听写流式WebAPI 服务，方言试用方法：登陆开放平台https://www.xfyun.cn/后，找到控制台--我的应用---语音听写（流式）---服务管理--识别语种列表
#  可添加语种或方言，添加后会显示该方言的参数值
#  错误码链接：https://www.xfyun.cn/document/error-code （code返回错误码时必看）
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
import logging

import math
import datetime
import hashlib
import base64
import hmac
import json
import pyaudio
import wave
from urllib.parse import urlencode
from aip import AipSpeech
import time
import ssl
from wsgiref.handlers import format_date_time
from datetime import datetime
from time import mktime
import _thread as thread
from sanic import websocket

STATUS_FIRST_FRAME = 0  # 第一帧的标识
STATUS_CONTINUE_FRAME = 1  # 中间帧标识
STATUS_LAST_FRAME = 2  # 最后一帧的标识


class WsParam(object):
    # 初始化
    def __init__(self, APPID, APIKey, APISecret, AudioFile):
        self.APPID = APPID
        self.APIKey = APIKey
        self.APISecret = APISecret
        self.AudioFile = AudioFile

        # 公共参数(common)
        self.CommonArgs = {"app_id": self.APPID}
        # 业务参数(business)，更多个性化参数可在官网查看
        self.BusinessArgs = {"domain": "iat", "language": "zh_cn", "accent": "mandarin", "vinfo": 1, "vad_eos": 5000}

    # 生成url
    def create_url(self):
        # url = 'wss://ws-api.xfyun.cn/v2/iat'
        url = 'wss://iat-api.xfyun.cn/v2/iat'
        # 生成RFC1123格式的时间戳
        now = datetime.now()
        date = format_date_time(mktime(now.timetuple()))

        # 拼接字符串
        signature_origin = "host: " + "ws-api.xfyun.cn" + "\n"
        signature_origin += "date: " + date + "\n"
        signature_origin += "GET " + "/v2/iat " + "HTTP/1.1"
        # 进行hmac-sha256进行加密
        signature_sha = hmac.new(self.APISecret.encode('utf-8'), signature_origin.encode('utf-8'),
                                 digestmod=hashlib.sha256).digest()
        signature_sha = base64.b64encode(signature_sha).decode(encoding='utf-8')

        authorization_origin = "api_key=\"%s\", algorithm=\"%s\", headers=\"%s\", signature=\"%s\"" % (
            self.APIKey, "hmac-sha256", "host date request-line", signature_sha)
        authorization = base64.b64encode(authorization_origin.encode('utf-8')).decode(encoding='utf-8')
        # 将请求的鉴权参数组合为字典
        v = {
            "authorization": authorization,
            "date": date,
            "host": "ws-api.xfyun.cn"
        }
        # 拼接鉴权参数，生成url
        url = url + '?' + urlencode(v)
        # print("date: ",date)
        # print("v: ",v)
        # 此处打印出建立连接时候的url,参考本demo的时候可取消上方打印的注释，比对相同参数时生成的url与自己代码生成的url是否一致
        # print('websocket url :', url)
        return url


# 收到websocket消息的处理
def on_message(ws, message):
    try:
        code = json.loads(message)["code"]
        sid = json.loads(message)["sid"]
        if code != 0:
            errMsg = json.loads(message)["message"]
            logging.info("sid: %s, call error: %s, code is: %s" % (sid, errMsg, code))

        else:
            data = json.loads(message)["data"]["result"]["ws"]
            result = ""
            for i in data:
                for w in i["cw"]:
                    result += w["w"]
            print("sid: %s, call success! data is: %s" % (sid, json.dumps(data, ensure_ascii=False)))
            print(f"result: {result}")
    except Exception as e:
        print("receive msg, but parse exception: ", e)


# 收到websocket错误的处理
def on_error(ws, error):
    print(f"### error: {error} ###")


# 收到 websocket 关闭的处理
def on_close(ws, a, b):
    print("### closed ###")


# 收到 websocket 连接建立的处理
def on_open(ws):
    def run(*args):
        frameSize = 8000  # 每一帧的音频大小
        intervel = 0.04  # 发送音频间隔(单位:s)
        status = STATUS_FIRST_FRAME  # 音频的状态信息，标识音频是第一帧，还是中间帧、最后一帧

        with open(wsParam.AudioFile, "rb") as fp:
            while True:
                buf = fp.read(frameSize)
                # 文件结束
                if not buf:
                    status = STATUS_LAST_FRAME
                # 第一帧处理
                # 发送第一帧音频，带 business 参数
                # appid 必须带上，只需第一帧发送
                # mp3 格式定义 lame，pcm 格式为 raw
                if status == STATUS_FIRST_FRAME:
                    d = {"common": wsParam.CommonArgs,
                         "business": wsParam.BusinessArgs,
                         "data": {"status": 0, "format": "audio/L16;rate=16000",
                                  "audio": str(base64.b64encode(buf), 'utf-8'),
                                  "encoding": "raw"}}
                    d = json.dumps(d)
                    ws.send(d)
                    status = STATUS_CONTINUE_FRAME
                # 中间帧处理
                elif status == STATUS_CONTINUE_FRAME:
                    d = {"data": {"status": 1, "format": "audio/L16;rate=16000",
                                  "audio": str(base64.b64encode(buf), 'utf-8'),
                                  "encoding": "raw"}}
                    ws.send(json.dumps(d))
                # 最后一帧处理
                elif status == STATUS_LAST_FRAME:
                    d = {"data": {"status": 2, "format": "audio/L16;rate=16000",
                                  "audio": str(base64.b64encode(buf), 'utf-8'),
                                  "encoding": "raw"}}
                    ws.send(json.dumps(d))
                    time.sleep(1)
                    break
                # 模拟音频采样间隔
                time.sleep(intervel)
        ws.close()

    thread.start_new_thread(run, ())


# 实时语音识别函数
def real_time_recognition(wsParam: WsParam):
    # 音频参数设置
    CHUNK = 1024
    FORMAT = pyaudio.paInt16
    CHANNELS = 1
    RATE = 16000
    p = pyaudio.PyAudio()

    stream = p.open(format=FORMAT, channels=CHANNELS, rate=RATE, input=True, frames_per_buffer=CHUNK)

    print("* 开始录音")

    frames = []
    # 用于记录静音帧的数量
    silent_frames = 0
    # 静音阈值，可以根据实际情况调整
    SILENCE_THRESHOLD = 500
    # 2 秒对应的帧数
    SILENCE_DURATION = int(1 * RATE / CHUNK)

    # RECORD_SECONDS = 5
    # for i in range(0, int(RATE / CHUNK * RECORD_SECONDS)):
    #     data = stream.read(CHUNK)
    #     frames.append(data)

    while True:
        data = stream.read(CHUNK)
        frames.append(data)

        # 计算音频数据块的能量（音量）
        audio_data = [int.from_bytes(data[i:i + 2], 'little', signed=True) for i in range(0, len(data), 2)]
        energy = math.sqrt(sum([x ** 2 for x in audio_data]) / len(audio_data))

        if energy < SILENCE_THRESHOLD:
            silent_frames += 1
            # 停顿时间超过指定时间对应的帧数，结束录音
            if silent_frames >= SILENCE_DURATION:
                break
        else:
            # 有语音输入，重置静音帧计数器
            silent_frames = 0

    print("* 录音结束")

    stream.stop_stream()
    stream.close()
    p.terminate()

    wf = wave.open(WAVE_OUTPUT_FILE_PATH, 'wb')
    wf.setnchannels(CHANNELS)
    wf.setsampwidth(p.get_sample_size(FORMAT))
    wf.setframerate(RATE)
    wf.writeframes(b''.join(frames))
    wf.close()

    # 调用音频文件识别函数
    recognize_audio_file(WAVE_OUTPUT_FILE_PATH, wsParam)


# 音频文件识别函数
def recognize_audio_file(audio_file_path, wsParam: WsParam):
    start_time = datetime.now()
    # wsParam = Ws_Param(APPID=APPID, APIKey=API_KEY, APISecret=API_SECRET, AudioFile=audio_file_path)
    wsParam.AudioFile = audio_file_path
    websocket.enableTrace(False)
    wsUrl = wsParam.create_url()
    ws = websocket.WebSocketApp(wsUrl, on_open=on_open, on_message=on_message, on_error=on_error, on_close=on_close)
    ws.run_forever(sslopt={"cert_reqs": ssl.CERT_NONE})
    end_time = datetime.now()
    print(f"time spend: {end_time - start_time}")


# 科大讯飞开放平台的相关信息
APPID = '00b791b9'
API_KEY = 'eecbc528ed5007744abf3a785118cd79'
API_SECRET = 'MmIzYzc1NjU3NTdjN2RlODNmYWNkYzM1'
# 科大讯飞语音听写的 WebSocket 地址
HOST = 'ws-api.xfyun.cn/v2/iat'
WAVE_OUTPUT_FILE_PATH = r'output.wav'

if __name__ == "__main__":
    choice = input("请选择识别方式（1: 音频文件识别，2: 实时语音识别）：")
    if choice == '1':
        wsParam = WsParam(APPID=APPID, APIKey=API_KEY, APISecret=API_SECRET, AudioFile=WAVE_OUTPUT_FILE_PATH)
        recognize_audio_file(WAVE_OUTPUT_FILE_PATH, wsParam)
    elif choice == '2':
        wsParam = WsParam(APPID=APPID, APIKey=API_KEY, APISecret=API_SECRET, AudioFile=None)
        real_time_recognition(wsParam)
    else:
        print("无效的选择，请输入 1 或 2")
