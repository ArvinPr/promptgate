from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass(frozen=True)
class TokenUsage:
    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None


@dataclass(frozen=True)
class GenerationResult:
    output: str
    provider: str
    model: str
    request_id: str
    usage: TokenUsage = field(default_factory=TokenUsage)
    latency_ms: int = 0
    cached: bool = False


class LLMProvider(ABC):
    @abstractmethod
    def generate(self, prompt: str) -> GenerationResult:
        raise NotImplementedError
