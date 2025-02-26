import pyttsx3

# 初始化语音引擎
engine = pyttsx3.init()

# 设置音量，通常是 0.0 到 1.0
engine.setProperty('volume', 1.0)

# 设置语速为 150，默认值是 200
engine.setProperty('rate', 150)


class TTS_Speaker:
    """
    Text-To-Speech
    """
    def __init__(self):
        pass

    @staticmethod
    def say(text: str):
        # 合成语音
        engine.say(text)
        # 运行引擎并等待语音合成完成
        engine.runAndWait()
