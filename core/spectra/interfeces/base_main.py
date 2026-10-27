from abc import ABC, abstractmethod
import numpy as np

class IProcessor(ABC):
    """
    Интерфейс основного обработчика.
    Задача: превратить сигнал в спектр (FFT, Welch и т.д.).
    """
    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    def process(self, signal: np.ndarray, fs: float) -> dict:
        """Возвращает словарь {'freqs': [...], 'amps': [...]}."""
        pass