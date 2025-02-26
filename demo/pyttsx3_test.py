import pyttsx3

# 初始化语音引擎
engine = pyttsx3.init()

# 设置音量，通常是 0.0 到 1.0
engine.setProperty('volume', 1.0)

# 设置语速为 150，默认值是 200
engine.setProperty('rate', 150)

if __name__ == '__main__':
    # 设置要合成的文本
    text = "欢迎使用 pyttsx3 进行语音合成。"
    # 合成语音
    engine.say(text)

    # 将语音保存到文件
    # engine.save_to_file(text, 'output.mp3')

    # 运行引擎并等待语音合成完成
    engine.runAndWait()