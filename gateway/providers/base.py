from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class GenerationResult:
    output: str
    provider: str
    model: str
    request_id: str


class LLMProvider(ABC):
    @abstractmethod
    def generate(self, prompt: str) -> GenerationResult:
        raise NotImplementedError
