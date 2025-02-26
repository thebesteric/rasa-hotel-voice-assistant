from aip import AipSpeech
import pyaudio
import wave

# 设置百度云的 APP_ID、API_KEY 和 SECRET_KEY
APP_ID = '117563065'
API_KEY = '7K0dZSgNBjeFCfvsu3CICuun'
SECRET_KEY = 'cAEeEOQazwOGYv5Oc6gpJBGEI1iDtMwr'

# 初始化 AipSpeech 对象
client = AipSpeech(APP_ID, API_KEY, SECRET_KEY)

# 音频文件识别函数
def recognize_audio_file(file_path):
    with open(file_path, 'rb') as fp:
        audio_data = fp.read()
    # 进行语音识别
    result = client.asr(audio_data, 'pcm', 16000, {
        'dev_pid': 1537,  # 普通话(支持简单的英文识别)
    })
    if result['err_no'] == 0:
        print("识别结果：", result['result'][0])
    else:
        print("识别失败：", result['err_msg'])

# 实时语音识别函数
def real_time_recognition():
    # 音频参数设置
    CHUNK = 1024
    FORMAT = pyaudio.paInt16
    CHANNELS = 1
    RATE = 16000
    RECORD_SECONDS = 5
    WAVE_OUTPUT_FILENAME = "output.wav"

    p = pyaudio.PyAudio()

    stream = p.open(format=FORMAT,
                    channels=CHANNELS,
                    rate=RATE,
                    input=True,
                    frames_per_buffer=CHUNK)

    print("* 开始录音")

    frames = []

    for i in range(0, int(RATE / CHUNK * RECORD_SECONDS)):
        data = stream.read(CHUNK)
        frames.append(data)

    print("* 录音结束")

    stream.stop_stream()
    stream.close()
    p.terminate()

    wf = wave.open(WAVE_OUTPUT_FILENAME, 'wb')
    wf.setnchannels(CHANNELS)
    wf.setsampwidth(p.get_sample_size(FORMAT))
    wf.setframerate(RATE)
    wf.writeframes(b''.join(frames))
    wf.close()

    # 调用音频文件识别函数
    recognize_audio_file(WAVE_OUTPUT_FILENAME)

if __name__ == "__main__":
    # 选择识别方式，1 为音频文件识别，2 为实时语音识别
    choice = input("请选择识别方式（1: 音频文件识别，2: 实时语音识别）：")
    if choice == '1':
        file_path = r"output.wav"
        recognize_audio_file(file_path)
    elif choice == '2':
        real_time_recognition()
    else:
        print("无效的选择，请输入 1 或 2。")