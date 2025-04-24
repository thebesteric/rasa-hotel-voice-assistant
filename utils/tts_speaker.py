import pyttsx3

# 初始化语音引擎
engine = pyttsx3.init()

# 设置音量，通常是 0.0 到 1.0
# 获取当前音量
engine.setProperty('volume', 1.0)
volume = engine.getProperty('volume')
print(f"当前音量：{volume}")

# 获取当前语速
engine.setProperty('rate', 160)
rate = engine.getProperty('rate')
print(f"当前语速：{rate}")

# 获取可用声音的列表
voices = engine.getProperty('voices')

# # 打印可用声音的信息
# for i, voice in enumerate(voices):
#     print(f"语音{i}:")
#     print(f" - ID: {voice.id}")
#     print(f" - 名称: {voice.name}")
#     print(f" - 语言: {voice.languages}")
#     print(f" - 性别: {voice.gender}")
#     print(f" - 年龄: {voice.age}")

# # 设置第二个声音（如果有的话）
# if len(voices) > 1:
#     engine.setProperty('voice', voices[1].id)
#     engine.say("这是使用另一个声音的效果")
#     engine.runAndWait()


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

    @staticmethod
    def say_and_save(text: str):
        engine.say(text)
        # 保存为 WAV 文件
        engine.save_to_file(text, './output.wav')
        engine.runAndWait()

if __name__ == '__main__':
    TTS_Speaker.say_and_save("你好，我是小爱同学。")
