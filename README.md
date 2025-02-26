### 启动 rasa 服务
```shell
rasa run --enable-api --cors "*" --debug --port 5005
```

### 启动 rasa action 服务
```shell
rasa run actions
```

### 启动 rasa 命令行交互
```shell
rasa shell
```

### 训练
```shell
rasa train
```

### 测试训练结果
```shell
rasa shell nlp
```