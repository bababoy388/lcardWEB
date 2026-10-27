from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import httpx
import struct
import numpy as np
import matplotlib

matplotlib.use('Agg')
import matplotlib.pyplot as plt
import io
import asyncio

from config import CPP_URL
from web.realtime.worker_realtime import run_realtime
from web.spectra.worker_spectra import run_spectra

app = FastAPI(title="L-Card Web")
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


# Запуск фоновых процессов при старте
@app.on_event("startup")
async def startup_event():
    asyncio.create_task(run_realtime())
    asyncio.create_task(run_spectra())


# --- Страницы ---
@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse(request, "index.html")


@app.get("/settings", response_class=HTMLResponse)
async def settings(request: Request):
    return templates.TemplateResponse(request, "settings.html")


# --- API Прокси ---
@app.get("/api/status")
async def api_status():
    async with httpx.AsyncClient() as client:
        r = await client.get(f"{CPP_URL}/status")
        return JSONResponse(r.json())


@app.get("/api/start")
async def api_start():
    async with httpx.AsyncClient() as client:
        r = await client.get(f"{CPP_URL}/start")
        return JSONResponse(r.json())


@app.get("/api/stop")
async def api_stop():
    async with httpx.AsyncClient() as client:
        r = await client.get(f"{CPP_URL}/stop")
        return JSONResponse(r.json())


@app.get("/api/ltrd/ip")
async def api_ltrd_ip():
    async with httpx.AsyncClient() as client:
        r = await client.get(f"{CPP_URL}/api/ltrd/ip")
        return JSONResponse(r.json())


# --- Генерация графиков (Matplotlib) ---
@app.get("/api/plot/wave")
async def plot_wave(n: int = 2000):
    async with httpx.AsyncClient() as client:
        r = await client.get(f"{CPP_URL}/data/all")
        if len(r.content) < 8: return JSONResponse({"error": "no data"})

        count = struct.unpack('<q', r.content[:8])[0]
        data = np.frombuffer(r.content[8:], dtype=np.float32).reshape(count, 5)

        # Берем последние n точек
        data = data[-n:]
        times = data[:, 0] - data[0, 0]  # Время от 0

        fig, ax = plt.subplots(figsize=(10, 3), facecolor='#161b22')
        ax.set_facecolor('#0d1117')
        ax.plot(times, data[:, 1], color='#e8b631', linewidth=0.8, label='CH1')
        ax.plot(times, data[:, 2], color='#4ecdc4', linewidth=0.8, label='CH2')
        ax.tick_params(colors='#8b949e')
        ax.grid(True, color='#30363d', alpha=0.5)
        ax.set_xlabel("Время, с", color='#8b949e')
        ax.set_ylabel("Напряжение, В", color='#8b949e')
        ax.legend(facecolor='#161b22', labelcolor='#e6edf3')

        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=100, bbox_inches='tight')
        plt.close(fig)
        buf.seek(0)
        return StreamingResponse(buf, media_type="image/png")