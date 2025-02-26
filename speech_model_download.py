if __name__ == '__main__':
    from modelscope import snapshot_download

    # 调用 snapshot_download 函数下载指定模型
    model_dir = snapshot_download('speech_paraformer-large-vad-punc_asr_nat-zh-cn-16k-common-vocab8404-pytorch')
    print(f"模型已下载到: {model_dir}")