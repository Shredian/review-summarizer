"""Клиент для взаимодействия с OpenAI API через LangChain."""

from typing import Optional

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage

from src.utils.logger import logger


class OpenAIClient:
    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4.1-mini",
        temperature: float = 1.0,
        max_retries: int = 3,
    ) -> None:
        self.model = model
        self.temperature = temperature
        self.max_retries = max_retries
        
        self._client = ChatOpenAI(
            api_key=api_key,
            model=model,
            temperature=temperature,
            max_retries=max_retries,
        )
        
        logger.debug(f"OpenAI клиент инициализирован с моделью {model}")

    async def send_request(
        self,
        prompt: str,
        temperature: Optional[float] = None,
    ) -> str:
        try:
            # Если указана другая температура, создаём временный клиент
            client = self._client
            if temperature is not None and temperature != self.temperature:
                client = ChatOpenAI(
                    api_key=self._client.openai_api_key,
                    model=self.model,
                    temperature=temperature,
                    max_retries=self.max_retries,
                )
            
            messages = [HumanMessage(content=prompt)]
            response = await client.ainvoke(messages)
            
            return response.content
            
        except Exception as e:
            logger.error(f"Ошибка при запросе к OpenAI API: {e}")
            raise

    async def send_request_json(
        self,
        prompt: str,
        temperature: Optional[float] = None,
    ) -> str:
        # Добавляем инструкцию о формате, если её нет
        if "json" not in prompt.lower():
            prompt = prompt + "\n\nОтвет должен быть только в формате JSON, без дополнительного текста."
        
        return await self.send_request(prompt, temperature)

    def __repr__(self) -> str:
        return f"OpenAIClient(model={self.model}, temperature={self.temperature})"
