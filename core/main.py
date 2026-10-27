from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import httpx
import struct
import numpy as np
import matplotlib
import io
import asyncio

# Отключаем GUI для Matplotlib (важно для работы на сервере без монитора)
matplotlib.use('Agg')
import matplotlib.pyplot as plt

# Импорты из вашей структуры
from config import CPP_URL
from realtime.worker_realtime import run_realtime
from spectra.worker_spectra import run_spectra


# ============================================================
# Управление жизненным циклом (Lifespan)
# Запускаем фоновые воркеры при старте и гасим при остановке
# ============================================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("[MAIN] Запуск фоновых процессов...")
    # Запускаем воркеры как фоновые задачи
    task_rt = asyncio.create_task(run_realtime())
    task_sp = asyncio.create_task(run_spectra())

    yield  # Здесь сервер работает и принимает запросы

    print("[MAIN] Остановка фоновых процессов...")
    task_rt.cancel()
    task_sp.cancel()


app = FastAPI(title="L-Card Web", lifespan=lifespan)

# Подключаем статику и шаблоны (пути относительны main.py)
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


# ============================================================
# HTML Страницы
# ============================================================
@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse(request, "index.html")


@app.get("/settings", response_class=HTMLResponse)
async def settings(request: Request):
    return templates.TemplateResponse(request, "settings.html")


# ============================================================
# API Прокси (Общается с C++ сервисом на порту 9005)
# ============================================================
async def fetch_from_cpp(endpoint: str):
    """Утилита для запросов в C++ с обработкой ошибок"""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get(f"{CPP_URL}{endpoint}")
            return JSONResponse(r.json(), status_code=r.status_code)
    except httpx.ConnectError:
        return JSONResponse({"error": "C++ сервис недоступен"}, status_code=503)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.get("/api/status")
async def api_status():
    return await fetch_from_cpp("/status")


@app.get("/api/start")
async def api_start():
    return await fetch_from_cpp("/start")


@app.get("/api/stop")
async def api_stop():
    return await fetch_from_cpp("/stop")


@app.get("/api/ltrd/ip")
async def api_ltrd_ip():
    return await fetch_from_cpp("/api/ltrd/ip")


# ============================================================
# Графики (Matplotlib)
# ============================================================
@app.get("/api/plot/wave")
async def plot_wave(n: int = 2000):
    """
    Скачивает бинарник из C++, берет последние n точек и рисует график.
    """
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.get(f"{CPP_URL}/data/all")

            if r.status_code != 200 or len(r.content) < 8:
                return JSONResponse({"error": "Нет данных в буфере"}, status_code=404)

            # 1. Парсим бинарник
            count = struct.unpack('<q', r.content[:8])[0]
            data = np.frombuffer(r.content[8:], dtype=np.float32).reshape(count, 5)

            # 2. Берем только последние n точек для отрисовки
            if count > n:
                data = data[-n:]

            # 3. Строим график
            times = data[:, 0] - data[0, 0]  # Время относительно начала окна

            # Используем стили "дарк"
            fig, ax = plt.subplots(figsize=(10, 3), facecolor='#161b22')
            ax.set_facecolor('#0d1117')

            # Рисуем CH1 и CH2
            ax.plot(times, data[:, 1], color='#e8b631', linewidth=0.8, label='CH1')
            ax.plot(times, data[:, 2], color='#4ecdc4', linewidth=0.8, label='CH2')

            # Настройка осей
            ax.tick_params(colors='#8b949e')
            ax.grid(True, color='#30363d', alpha=0.5)
            ax.set_xlabel("Время, с", color='#8b949e')
            ax.set_ylabel("Напряжение, В", color='#8b949e')
            ax.legend(facecolor='#161b22', labelcolor='#e6edf3', loc='upper right')

            # Сохраняем в память (без файла)
            buf = io.BytesIO()
            plt.savefig(buf, format='png', dpi=100, bbox_inches='tight')
            plt.close(fig)  # ОБЯЗАТЕЛЬНО закрываем фигуру, иначе будет утечка памяти
            buf.seek(0)

            return StreamingResponse(buf, media_type="image/png")

    except httpx.ConnectError:
        return JSONResponse({"error": "C++ сервис недоступен"}, status_code=503)
    except Exception as e:
        print(f"[PLOT ERROR] {e}")
        return JSONResponse({"error": str(e)}, status_code=500)