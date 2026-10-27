from abc import ABC, abstractmethod
import numpy as np

class IPreProcessor(ABC):
    """
    Интерфейс предобработчика.
    Задача: взять сырой сигнал, отфильтровать, проинтегрировать или выделить огибающую.
    """
    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    def process(self, signal: np.ndarray, fs: float) -> np.ndarray:
        """Возвращает преобразованный 1D-массив (сигнал)."""
        pass