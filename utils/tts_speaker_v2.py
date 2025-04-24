import os

import pyttsx3


class TTSSpeaker:
    def __init__(self, volume=1.0, rate=160, on_start=None, on_word=None, on_end=None):
        # 初始化语音引擎
        self.engine = pyttsx3.init()

        self.engine.connect('started-utterance', on_start)
        self.engine.connect('started-word', on_word)
        self.engine.connect('finished-utterance', on_end)

        # 设置音量，通常是 0.0 到 1.0
        self.engine.setProperty('volume', volume)

        # 获取当前语速，默认为 200
        self.engine.setProperty('rate', rate)

        # 获取可用声音的列表
        self.voices = self.engine.getProperty('voices')

    def say(self, text: str):
        # 合成语音
        self.engine.say(text)
        # 运行引擎并等待语音合成完成
        self.engine.runAndWait()

    def save(self, text: str, file_path: str = "./output.wav"):
        # 要调用一下 say 方法，否则 save_to_file 报错
        # self.engine.say(text)
        # 保存为音频文件
        self.engine.save_to_file(text, file_path)
        # 运行引擎并等待语音合成完成
        self.engine.runAndWait()
        # 获取合成后的文件，并返回完整的路径
        # 相对路径转换为绝对路径
        return file_path if os.path.isabs(file_path) else os.path.abspath(file_path)

if __name__ == '__main__':

    speaker = TTSSpeaker(rate=170)
    print(speaker.save("你好，我是你的语音助手"))
