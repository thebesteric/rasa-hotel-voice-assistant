import threading


class Thread_Local_Utils:
    # 初始化一个线程局部变量对象
    _thread_local = threading.local()

    @classmethod
    def set_variable(cls, key, value):
        """
        保存线程的变量
        :param key: 变量的键
        :param value: 变量的值
        """
        if not hasattr(cls._thread_local, 'variables'):
            cls._thread_local.variables = {}
        cls._thread_local.variables[key] = value

    @classmethod
    def get_variable(cls, key, default=None):
        """
        获取线程的变量
        :param key: 变量的键
        :param default: 如果键不存在，返回的默认值
        :return: 变量的值
        """
        if hasattr(cls._thread_local, 'variables') and key in cls._thread_local.variables:
            return cls._thread_local.variables[key]
        return default

    @classmethod
    def clear_variables(cls):
        """
        清空线程的所有变量
        """
        if hasattr(cls._thread_local, 'variables'):
            cls._thread_local.variables = {}
