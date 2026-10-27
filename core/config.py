import os

# Адреса C++ движка
CPP_URL = "http://127.0.0.1:9005"
CPP_WS = "ws://127.0.0.1:9006"

# Адрес внешней системы
CYBERSTUDIO_URL = "http://cyberstudio.api/upload"

# Точная частота дискретизации (29297 = 29296.875 Гц)
FS_EXACT = 29296.875

# Параметры анализа
THRESHOLD_PEAK = 2.0     # Порог ускорения для тревоги (g)
COOLDOWN_SEC = 60.0      # Пауза между отправками событий
HISTORY_SEC = 10.0       # Сколько секунд хранить для события (5 до + 5 после)

SPECTRA_INTERVAL_SEC = 10

REST_INTERVAL_SEC = 60