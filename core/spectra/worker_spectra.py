import asyncio
import httpx
import numpy as np
import struct
import time

from core.config import CPP_URL, REST_INTERVAL_SEC


async def fetch_data():
    """Скачивает бинарник из C++ и превращает его в матрицу numpy"""
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            print("[REST] Запрос данных /data/all...")
            r = await client.get(f"{CPP_URL}/data/all")

            if r.status_code != 200 or len(r.content) < 8:
                print("[REST] Нет данных или ошибка сервера.")
                return None

            # 1. Читаем заголовок (8 байт - сколько точек)
            count = struct.unpack('<q', r.content[:8])[0]

            # 2. Читаем остальное как float32 (5 колонок)
            data = np.frombuffer(r.content[8:], dtype=np.float32).reshape(count, 5)
            return data

        except Exception as e:
            print(f"[REST] Ошибка сети: {e}")
            return None


async def run_spectra():
    print(f"[REST] Воркер запущен. Интервал: {REST_INTERVAL_SEC} сек.")

    while True:
        await asyncio.sleep(REST_INTERVAL_SEC)

        start_time = time.time()
        data = await fetch_data()

        if data is not None:
            # Выводим базовую статистику, чтобы понять, что данные адекватные
            print(f"\n[REST] ✅ Успешно скачано {len(data):,} точек.")
            print(f"[REST] Формат матрицы: {data.shape}")

            # Смотрим значения по первому каналу (индекс 1)
            ch0 = data[:, 1]
            print(f"[REST] CH1: Мин={np.min(ch0):.3f} В, Макс={np.max(ch0):.3f} В, Среднее={np.mean(ch0):.3f} В")

            # Считаем примерную частоту по разнице времени
            if len(data) > 10:
                dt = data[1, 0] - data[0, 0]
                print(f"[REST] Шаг времени: {dt:.9f} с (Частота: {1 / dt:.1f} Гц)")

            print(f"[REST] Скачивание и парсинг заняли: {time.time() - start_time:.3f} сек.\n")

            # Здесь в будущем будет вызов Фабрики, но пока просто заглушка
            # spectra = factory.process_all(ch0, FS_EXACT)

        else:
            print("[REST] Данных нет. Ждем следующего цикла...\n")


if __name__ == "__main__":
    try:
        asyncio.run(run_spectra())
    except KeyboardInterrupt:
        print("\n[REST] Остановлено пользователем.")