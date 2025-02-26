from typing import Any, Dict, Text, List
from rasa.engine.graph import GraphComponent, ExecutionContext
from rasa.engine.recipes.default_recipe import DefaultV1Recipe
from rasa.engine.storage.resource import Resource
from rasa.engine.storage.storage import ModelStorage
from rasa.shared.nlu.training_data.message import Message
from rasa.nlu.classifiers.classifier import IntentClassifier
from rasa.shared.nlu.training_data.training_data import TrainingData



@DefaultV1Recipe.register(DefaultV1Recipe.ComponentType.INTENT_CLASSIFIER, is_trainable=False)
class MessageMiddleware(GraphComponent, IntentClassifier):
    def __init__(self, config: Dict[Text, Any]):
        self.config = config
        self.name = "message_middleware"

    @classmethod
    def create(
        cls,
        config: Dict[Text, Any],
        model_storage: ModelStorage,
        resource: Resource,
        execution_context: ExecutionContext,
    ) -> GraphComponent:
        return cls(config)

    def process(self, messages: List[Message]) -> List[Message]:
        for message in messages:
            # 获取当前消息的文本
            text = message.get("text")
            # logging.info(f"[{self.name}] 当前消息的文本: {text}")
        return messages



