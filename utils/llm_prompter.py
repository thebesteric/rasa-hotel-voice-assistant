class LLM_Prompter:
    ROOM_UN_CLEAM_SLOTS_PROMPT = """
                    ### 你的角色: 你精通 NLP 领域，擅长分析文本，提取意图和槽位信息
                    ### 当前任务: 请提取这句话中的槽位信息：{user_input}
                    ### 任务要求：需要提取的槽位如下：
                    - 房间号（room_un_clean_room_no）：表示未打扫的房间编号
                    - 提醒时间（room_un_clean_remind_time）：转化为分钟
                      - 提醒时间为小数类型则向上取整
                      - 非数字的情况：如：一刻钟，则转换为 15 分钟，半个小时，则转换为 30 分钟；1.5 小时，则转换为 90 分钟
                      - 提醒时间涉及到到含有今天、明天、后天，上午、下午等情况，则将 room_un_clean_remind_time 设置为 null，并写入异常信息到 exception 中，参考异常处理流程
                    - 时间单位（room_un_clean_remind_time_unit）：固定为分钟
                    ### 异常处理: 
                    - 当 room_un_clean_room_no 未提取到的时候，room_un_clean_room_no 设置为 null
                    - 当 room_un_clean_remind_time 无法解析时，设置为 null，并将异常原因填写到 exception 中，其中 field 为无法解析的内容，cause 为无法解析的原因
                    ### 返回结果: 请以 JSON 格式返回提取结果，{think_response_message}，示例如下：
                    - 正常实例
                    ```json
                    {{
                      "room_un_clean_room_no": "801",
                      "room_un_clean_remind_time": 30,
                      "room_un_clean_remind_time_unit": "分钟"
                      "exception": null
                    }}
                    ```
                    - 异常实例
                    ```json
                    {{
                      "room_un_clean_room_no": "801",
                      "room_un_clean_remind_time": null,
                      "room_un_clean_remind_time_unit": "分钟"
                      "exception": {{
                        "field": "今天下午三点",
                        "cause": "无法将今天下午三点转为为分钟"
                      }}
                    }}
                    ```
                    """

    ROOM_REPLENISHMENT = """
        ### 角色：你精通自然语言处理和理解，对槽位提取非常擅长
        ### 任务：{user_input}
        ### 要求：提取相关槽位信息，如下所示：
        #### 槽位要求：
        - 房间号：room_no，字符串
        - 商品名称：name，字符串
        - 商品数量：quantity，整型
        - 数量单位：unit，字符串
        #### 其他要求：
        - 当遇到中文的数字大写，如：一、二、三...百、千、万等和壹、贰、叁...佰，仟，万等中文大写，均转换为对应的阿拉伯数字
        ### 异常处理：当某个槽位解析失败或无法解析时，用 null 填充
        ### 输出格式：只输出 json 格式，不需要其他任何额外信息，包括思考和分析逻辑
        - 案例一：802房间补货，1袋咖啡，2瓶沐浴露
        ```json
        {{
            room_no: "802",
            items: [
            {{
                "name": "咖啡",
                “unit": "袋",
                "quantity": 1
            }},
            {{
                "name": "沐浴露",
                "unit": "瓶",
                "quantity": 2
            }}
        }}
        ```
    """

    @staticmethod
    def handle_think_response(think_response: bool) -> str:
        return "同时返回思考和分析过程的数据" if think_response else "不返回思考和分析过程的数据，以及其他任何额外信息，包括思考和分析逻辑"

    @staticmethod
    def room_un_clean_slots_prompt(user_input: str, think_response: bool = False) -> str:
        think_response_message = LLM_Prompter.handle_think_response(think_response)
        return LLM_Prompter.ROOM_UN_CLEAM_SLOTS_PROMPT.format(user_input=user_input,
                                                              think_response_message=think_response_message)

    @staticmethod
    def room_replenishment_prompt(user_input: str, think_response: bool = False) -> str:
        think_response_message = LLM_Prompter.handle_think_response(think_response)
        return LLM_Prompter.ROOM_REPLENISHMENT.format(user_input=user_input,
                                                      think_response_message=think_response_message)
