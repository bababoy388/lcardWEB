import asyncio
import websockets
import numpy as np
import time

from core.config import CPP_WS


async def run_realtime():
    print("[REALTIME] Подключение к C++ WebSocket...")

    while True:
        try:
            async with websockets.connect(CPP_WS) as ws:
                print("[REALTIME] ✅ Успешно подключено к потоку данных.")

                while True:
                    # Ждем бинарный фрейм
                    msg = await ws.recv()
                    if not msg: continue

                    # C++ отправляет float32: [time, ch0, ch1, ch2, ch3]
                    data = np.frombuffer(msg, dtype=np.float32).reshape(-1, 5)

                    if len(data) > 0:
                        # Берем первую точку из блока для примера
                        t = data[0, 0]
                        ch0 = data[0, 1]
                        ch1 = data[0, 2]

                        # Выводим, чтобы видеть, что поток идет
                        print(
                            f"[WS] Получено {len(data):4d} точек | Время: {t:.3f} | CH1: {ch0:6.3f} В | CH2: {ch1:6.3f} В")

        except websockets.exceptions.ConnectionClosed:
            print("[REALTIME] Соединение закрыто. Переподключение через 3 сек...")
            await asyncio.sleep(3)
        except Exception as e:
            print(f"[REALTIME] Ошибка: {e}. Переподключение через 3 сек...")
            await asyncio.sleep(3)


if __name__ == "__main__":
    try:
        asyncio.run(run_realtime())
    except KeyboardInterrupt:
        print("\n[REALTIME] Остановлено пользователем.")