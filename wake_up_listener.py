import logging
import time

from funasr import AutoModel
import sounddevice as sd
import numpy as np
from pypinyin import lazy_pinyin
import re
import threading
import asyncio
import sys
import os

# 清除已有的日志处理器
logging.getLogger().handlers = []
# 配置日志记录
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', stream=sys.stdout)

# 获取当前脚本所在的目录
current_dir = os.path.dirname(os.path.abspath(__file__))
# 构建目录路径
rasa_utils_dir = os.path.abspath(os.path.join(current_dir, 'utils'))
# 将目录添加到系统路径中
sys.path.append(rasa_utils_dir)

# 导入文件
try:
    from tts_speaker import TTS_Speaker
    from rasa_caller import Rasa_Caller, Dialog
    from asr_caller import ASR_Caller
except ImportError as e:
    print(f"文件导入失败：{e}，无法导入 {rasa_utils_dir} 文件，请检查文件路径和内容。")

# 模型参数设置
chunk_size = [0, 10, 5]
encoder_chunk_look_back = 7
decoder_chunk_look_back = 5

model = AutoModel(model="asserts/lib/speech_paraformer-large-vad-punc_asr_nat-zh-cn-16k-common-vocab8404-pytorch",
                  disable_update=True)

# 假设模型要求的采样率为 16000
fs = 16000
# 每次录制音频的时长，单位为秒
duration = 3
# 语音识别的步长
chunk_stride = chunk_size[1] * 960
# 缓存语音识别的中间结果
cache = {}
# 噪声处理的窗口大小
window_size = 3

# 录音结束后静音等待时间（毫秒）
VAD_EOS = 1000
# 录音开始前静音等待时间（秒）
SILENCE_DURATION_FACTOR = 2

# 语义识别
asr_caller = ASR_Caller(vad_eos=VAD_EOS)

WAKE_UP_KEYWORDS = ["小住小住", "小度小度", "小住小度", "小度小住", "住小住", "度小度", "住小度", "度小住", "小住小",
                    "小度小", "小住小", "小度小"]
GREETING_WORDS = ["我在，需要我帮你做什么？", "在呢", "我在，有什么可以帮你的吗？", "在的，有什么吩咐么？", "我在"]

# 创建线程锁
lock = threading.Lock()


def format_to_pinyin(message: str) -> str:
    # 去除特殊字符（标点符号）
    message = re.sub(r'[^\w\s]', '', message)
    # 结果转换为拼音，并去除空格
    return ''.join(lazy_pinyin(message)).replace(" ", "")


def any_keywords_in_sentence(wake_up_keywords: list[str], sentence: str):
    # 将句子转换为小写，以便不区分大小写进行比较
    for keywords in wake_up_keywords:
        # 判断单词是否在句子中
        if keywords in sentence:
            return True
    return False


def call_method():
    current_thread_name = threading.current_thread().name
    try:
        logging.info(f"[{current_thread_name}] call_method 开始执行")

        while True:
            message = asr_caller.recognize_real_time(r"./voice_output/output.wav",
                                                     silence_duration_factor=SILENCE_DURATION_FACTOR)
            logging.info(f"[{current_thread_name}] ===> 用户语音识别结果: {message}")
            # 用户没有说话，则跳出循环，并中断会话
            if not message:
                Rasa_Caller.send(sender="sender_1", message="中断流程")
                break
            # 调用 Rasa 进行执行任务
            dialogs = Rasa_Caller.send(sender="sender_1", message=message)
            text_dialogs = Dialog.get_text_dialogs(dialogs)
            for text_dialog in text_dialogs:
                logging.info(f"[{current_thread_name}] ===> Rasa 响应: {text_dialog.text}")
                TTS_Speaker.say(text_dialog.text)
                time.sleep(1)
            restart_process_true_dialogs = Dialog.get_custom_dialogs_with_restart_process_true(dialogs)
            print("restart_process_true_dialogs ===> ", restart_process_true_dialogs)
            if restart_process_true_dialogs:
                logging.info(f"[{current_thread_name}] ===> Rasa 会话结束")
                break

        logging.info(f"[{current_thread_name}] call_method 执行完毕")
    finally:
        # 确保在方法结束时解锁
        lock.release()


# 唤醒词（拼音），去除特殊字符（标点符号）
WAKE_UP_KEYWORDS_PINYIN = []
for keyword in WAKE_UP_KEYWORDS:
    WAKE_UP_KEYWORDS_PINYIN.append(format_to_pinyin(keyword))


def start_listening():
    while True:
        start_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        recording = sd.rec(int(fs * duration), samplerate=fs, channels=1)
        # 等待录制完成
        sd.wait()
        # 将录制的音频数据展平为一维数组
        speech_chunk = recording.flatten()
        # 对音频数据进行噪声处理，使用卷积操作
        filtered_chunk = np.convolve(speech_chunk, np.ones(window_size) / window_size, mode='same')
        speech_chunk = filtered_chunk

        is_final = False
        # 调用语音识别模型进行语音识别
        res = model.generate(input=speech_chunk, cache=cache, is_final=is_final, chunk_size=chunk_size,
                             encoder_chunk_look_back=encoder_chunk_look_back,
                             decoder_chunk_look_back=decoder_chunk_look_back)
        # 获取识别结果
        text_result = str(res[0]['text'])
        text_result_pinyin = format_to_pinyin(text_result)

        # 打印日志
        logging.info(f"start_time: {start_time}, text_result: {text_result}, text_result_pinyin: {text_result_pinyin}")

        # 判断是否命中唤醒词
        if any_keywords_in_sentence(WAKE_UP_KEYWORDS_PINYIN, text_result_pinyin):
            # 从 GREETING_WORDS 随机选择一个句子进行回复
            greeting_sentence = np.random.choice(GREETING_WORDS)
            TTS_Speaker.say(greeting_sentence)
            # 获取锁
            lock.acquire()
            # 调用方法
            call_method()


if __name__ == '__main__':
    try:
        start_listening()
    except Exception as e:
        logging.error(f"发生异常: {e}", exc_info=True)
