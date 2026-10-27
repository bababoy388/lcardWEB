from abc import ABC, abstractmethod

class IPostProcessor(ABC):
    """
    Интерфейс постобработчика.
    Задача: модифицировать уже готовый спектр (масштабирование, поиск пиков, форматирование).
    """
    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    def process(self, spectrum: dict, fs: float) -> dict:
        """Возвращает модифицированный словарь {'freqs': [...], 'amps': [...]}."""
        pass