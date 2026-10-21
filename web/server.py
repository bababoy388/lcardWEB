from pathlib import Path
from datetime import datetime
from typing import Optional
import re
import struct

from fastapi import FastAPI, Request, HTTPException, Query, Response
from fastapi.responses import HTMLResponse, PlainTextResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import httpx
from collections import deque
import numpy as np

import plot  # наш модуль matplotlib


# ============================================================
# Пути
# ============================================================
BASE_DIR     = Path(__file__).resolve().parent
TEMPLATE_DIR = BASE_DIR / "templates"
STATIC_DIR   = TEMPLATE_DIR / "static"


def _find_data_dir() -> Path:
    for d in [BASE_DIR.parent, BASE_DIR]:
        try:
            if any(d.glob("data_*.csv")) or any(d.glob("run_*.csv")):
                return d
        except Exception:
            pass
    return BASE_DIR.parent


DATA_DIR = _find_data_dir()
print(f"[WEB] BASE_DIR = {BASE_DIR}")
print(f"[WEB] DATA_DIR = {DATA_DIR}  (exists={DATA_DIR.exists()})")


# ============================================================
# FastAPI
# ============================================================
app = FastAPI(title="L-Card Web")
templates = Jinja2Templates(directory=str(TEMPLATE_DIR))

if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
else:
    print(f"[WEB] ВНИМАНИЕ: {STATIC_DIR} не найдена")

CPP_URL = "http://127.0.0.1:9005"
TIMEOUT = 10.0

TS_FMT = "%Y-%m-%d %H:%M:%S.%f"


# ============================================================
# HTML-страницы
# ============================================================
@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse(request, "index.html")


@app.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request):
    return templates.TemplateResponse(request, "settings.html")


@app.get("/files", response_class=HTMLResponse)
async def files_page(request: Request):
    return templates.TemplateResponse(request, "files.html")

# ============================================================
# Страница крейтов
# ============================================================
@app.get("/crates", response_class=HTMLResponse)
async def crates_page(request: Request):
    return templates.TemplateResponse(request, "crates.html")


# ============================================================
# Прокси: ltrd IP-адреса и крейты
# ============================================================
@app.get("/api/ltrd/ip")
async def api_ltrd_ip_list():
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            r = await client.get(f"{CPP_URL}/api/ltrd/ip")
            return JSONResponse(r.json(), status_code=r.status_code)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=503)


@app.post("/api/ltrd/ip")
async def api_ltrd_ip_add(payload: dict):
    params = {}
    for k, v in payload.items():
        if v is None:
            continue
        if isinstance(v, bool):
            params[k] = "true" if v else "false"
        else:
            params[k] = str(v)
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            r = await client.post(f"{CPP_URL}/api/ltrd/ip", params=params)
            return JSONResponse(r.json(), status_code=r.status_code)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=503)


@app.delete("/api/ltrd/ip")
async def api_ltrd_ip_delete(ip: str = Query(...), permanent: bool = True):
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            r = await client.delete(
                f"{CPP_URL}/api/ltrd/ip",
                params={"ip": ip, "permanent": "true" if permanent else "false"},
            )
            return JSONResponse(r.json(), status_code=r.status_code)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=503)


@app.get("/api/ltrd/crates")
async def api_ltrd_crates():
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            r = await client.get(f"{CPP_URL}/api/ltrd/crates")
            return JSONResponse(r.json(), status_code=r.status_code)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=503)


# ============================================================
# Прокси к C++
# ============================================================
@app.get("/api/status")
async def api_status():
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            r = await client.get(f"{CPP_URL}/status")
            return JSONResponse(r.json())
    except Exception as e:
        return JSONResponse({"error": str(e), "cpp_online": False}, status_code=503)


@app.get("/api/config")
async def api_config():
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            r = await client.get(f"{CPP_URL}/config")
            return JSONResponse(r.json())
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=503)


@app.post("/api/config")
async def api_config_set(payload: dict):
    params = {}
    for k, v in payload.items():
        if v is None: continue
        if isinstance(v, bool):
            params[k] = "true" if v else "false"
        else:
            params[k] = str(v)
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            r = await client.post(f"{CPP_URL}/config", params=params)
            return JSONResponse(r.json())
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=503)


@app.get("/api/start")
@app.post("/api/start")
async def api_start():
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            r = await client.get(f"{CPP_URL}/start")
            return JSONResponse(r.json())
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=503)


@app.get("/api/stop")
@app.post("/api/stop")
async def api_stop():
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            r = await client.get(f"{CPP_URL}/stop")
            return JSONResponse(r.json())
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=503)


@app.get("/api/buffer/clear")
@app.post("/api/buffer/clear")
async def api_clear():
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            r = await client.get(f"{CPP_URL}/buffer/clear")
            return JSONResponse(r.json())
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=503)


# ============================================================
# Список файлов
# ============================================================
def _parse_filename_time(name: str) -> Optional[datetime]:
    m = re.search(r"(\d{8})_(\d{6})", name)
    if not m:
        return None
    try:
        return datetime.strptime(m.group(1) + m.group(2), "%Y%m%d%H%M%S")
    except ValueError:
        return None


def _parse_ts(s: str) -> Optional[datetime]:
    try:
        return datetime.strptime(s.strip(), TS_FMT)
    except Exception:
        try:
            return datetime.strptime(s.strip(), "%Y-%m-%d %H:%M:%S")
        except Exception:
            return None


def _file_time_range(path: Path):
    """
    Возвращает (ts_first, ts_last) — datetime начала и конца по timestamp внутри файла.
    Читает первую строку данных и последнюю. None, если не удалось.
    """
    try:
        with open(path, "r", encoding="utf-8") as f:
            header = f.readline().strip()
            if not header:
                return None, None

            # Первая строка данных
            first_line = None
            for line in f:
                line = line.strip()
                if line:
                    first_line = line
                    break
            if not first_line:
                return None, None

            first_ts = _parse_ts(first_line.split(",", 1)[0])
            if first_ts is None:
                return None, None

            # Последняя строка
            last_line = first_line
            for line in f:
                line = line.strip()
                if line:
                    last_line = line
            last_ts = _parse_ts(last_line.split(",", 1)[0])
            if last_ts is None:
                last_ts = first_ts

            return first_ts, last_ts
    except Exception as e:
        print(f"[FILES] error {path.name}: {e}")
        return None, None


def _list_data_files():
    files = []
    for f in DATA_DIR.glob("*.csv"):
        if f.name.endswith("_spectrum.csv"):
            continue
        try:
            st = f.stat()
        except OSError:
            continue
        ts_first, ts_last = _file_time_range(f)
        files.append({
            "name": f.name,
            "size": st.st_size,
            "mtime": st.st_mtime,
            "mtime_str": datetime.fromtimestamp(st.st_mtime).strftime("%d.%m.%y %H:%M:%S"),
            "start_dt": _parse_filename_time(f.name),
            "ts_first": ts_first,
            "ts_last":  ts_last,
        })
    files.sort(key=lambda x: x["mtime"], reverse=True)
    return files


@app.get("/api/files")
async def api_files():
    files_out = []
    for f in _list_data_files():
        files_out.append({
            "name":      f["name"],
            "size":      f["size"],
            "mtime_str": f["mtime_str"],
            "start_dt":  f["start_dt"].strftime(TS_FMT) if f["start_dt"] else None,
            "ts_first":  f["ts_first"].strftime(TS_FMT) if f["ts_first"] else None,
            "ts_last":   f["ts_last"].strftime(TS_FMT) if f["ts_last"] else None,
        })
    return JSONResponse({
        "dir":   str(DATA_DIR),
        "files": files_out,
    })


@app.get("/api/files/download/{name}")
async def api_file_download(name: str):
    if "/" in name or "\\" in name or ".." in name:
        raise HTTPException(status_code=400, detail="invalid name")
    path = DATA_DIR / name
    if not path.exists():
        raise HTTPException(status_code=404, detail="file not found")

    from fastapi.responses import FileResponse
    return FileResponse(
        path=str(path),
        media_type="text/csv",
        filename=name,
    )


@app.get("/api/files/latest")
async def api_files_latest():
    files = _list_data_files()
    if not files:
        return JSONResponse({"name": None}, status_code=404)
    return JSONResponse({"name": files[0]["name"]})


@app.get("/api/files/{name}")
async def api_file_get(name: str):
    if "/" in name or "\\" in name or ".." in name:
        raise HTTPException(status_code=400, detail="invalid name")
    path = DATA_DIR / name
    if not path.exists():
        raise HTTPException(status_code=404, detail="file not found")
    return PlainTextResponse(path.read_text(encoding="utf-8"),
                             media_type="text/csv")


# ============================================================
# Чтение CSV
# ============================================================
def _read_all_rows(path: Path, dt_from: datetime, dt_to: datetime):
    cols = []
    rows = []
    with open(path, "r", encoding="utf-8") as f:
        header = f.readline().strip()
        if not header:
            return cols, rows
        cols = [c.strip() for c in header.split(",")]
        for line in f:
            line = line.strip()
            if not line:
                continue
            ts_str = line.split(",", 1)[0].strip()
            ts = _parse_ts(ts_str)
            if ts is None:
                continue
            if ts < dt_from:
                continue
            if ts > dt_to:
                break
            rows.append(line.split(","))
    return cols, rows


def _read_last_rows(path: Path, n: int):
    with open(path, "r", encoding="utf-8") as f:
        header = f.readline().strip()
        if not header:
            return [], []
        cols = [c.strip() for c in header.split(",")]
        rows = deque(maxlen=n)
        for line in f:
            line = line.strip()
            if line:
                rows.append(line.split(","))
    return cols, rows


def _to_np(cols, rows):
    if not rows:
        return np.array([]), {}

    n = len(rows)
    ts_str_list = [r[0].strip() for r in rows]
    try:
        ts_arr = np.array(ts_str_list, dtype="datetime64[us]")
    except Exception:
        ts_arr = None

    if ts_arr is not None:
        t0 = ts_arr[0]
        times = (ts_arr - t0).astype("timedelta64[us]").astype(float) / 1e6
    else:
        parsed = [_parse_ts(s) for s in ts_str_list]
        valid = [t for t in parsed if t]
        t0 = valid[0] if valid else None
        if t0 is None:
            times = np.arange(n, dtype=float)
        else:
            times = np.array([
                (t - t0).total_seconds() if t else 0.0 for t in parsed
            ])

    chans = {}
    for i, name in enumerate(cols[1:]):
        arr = np.empty(n, dtype=float)
        for j, r in enumerate(rows):
            try:
                arr[j] = float(r[i + 1])
            except (ValueError, IndexError):
                arr[j] = np.nan
        chans[name] = np.nan_to_num(arr, nan=0.0)
    return times, chans


# ============================================================
# Получение данных для диапазона
# ============================================================
def _iso_to_dt(s: str) -> datetime:
    s = s.strip().replace("T", " ")
    if s.endswith("Z"):
        s = s[:-1]
    if "." not in s:
        s += ".000000"
    else:
        head, frac = s.rsplit(".", 1)
        frac = (frac + "000000")[:6]
        s = head + "." + frac
    return datetime.strptime(s, TS_FMT)


def _get_data_for_range(from_: Optional[str], to_: Optional[str], max_points: int):
    files = _list_data_files()
    if not files:
        return None, None, None

    # Режим «последние N точек»
    if not from_ or not to_:
        path = DATA_DIR / files[0]["name"]
        cols, rows = _read_last_rows(path, max_points)
        if not cols or not rows:
            return None, None, None
        times, chans = _to_np(cols, rows)
        return times, chans, path.name

    try:
        dt_from = _iso_to_dt(from_)
        dt_to   = _iso_to_dt(to_)
    except Exception:
        return None, None, None

    all_cols = None
    all_rows = []
    used = []
    for f in files:
        if f["start_dt"] and f["start_dt"] > dt_to:
            continue
        path = DATA_DIR / f["name"]
        try:
            c, r = _read_all_rows(path, dt_from, dt_to)
        except Exception:
            continue
        if not c or not r:
            continue
        if all_cols is None:
            all_cols = c
        used.append(f["name"])
        all_rows.extend(r)

    if all_cols is None or not all_rows:
        return None, None, None

    times, chans = _to_np(all_cols, all_rows)
    label = ", ".join(used[:3]) + (f" (+{len(used)-3})" if len(used) > 3 else "")
    return times, chans, label


# ============================================================
# /api/monitor (JSON — оставим для совместимости, но не используем)
# ============================================================
@app.get("/api/monitor")
async def api_monitor(
    from_: Optional[str] = Query(None, alias="from"),
    to_:   Optional[str] = Query(None, alias="to"),
    n:     int = 4096,
):
    times, chans, label = _get_data_for_range(from_, to_, n)
    if times is None or len(times) < 4:
        return JSONResponse({"error": "no data"}, status_code=404)

    dt = float(np.mean(np.diff(times)))
    fs = 1.0 / dt if dt > 0 else 14000.0

    N_FFT = 4096
    spectrum_freqs = None
    spectrum_amps = []
    hist_edges = None
    hist_counts = []
    channels_out = []

    for name, arr in chans.items():
        arr = np.asarray(arr, dtype=float)
        mn, mx = float(np.min(arr)), float(np.max(arr))
        rms = float(np.sqrt(np.mean(arr * arr)))
        sigma = float(np.std(arr))

        seg = arr[-N_FFT:] if len(arr) > N_FFT else arr
        if len(seg) < N_FFT:
            seg = np.pad(seg, (0, N_FFT - len(seg)))
        win = np.hanning(len(seg))
        seg_w = (seg - np.mean(seg)) * win
        fft_vals = np.fft.rfft(seg_w)
        freqs = np.fft.rfftfreq(len(seg), d=1.0 / fs)
        amps = np.abs(fft_vals) * 2.0 / np.sum(win)
        if len(amps) > 0:
            amps[0] /= 2.0

        spectrum_freqs = freqs.tolist()
        spectrum_amps.append(amps.tolist())

        counts, edges = np.histogram(arr, bins=25)
        hist_edges = edges.tolist()
        hist_counts.append(counts.tolist())

        channels_out.append({
            "name": name,
            "data": arr.tolist(),
            "min": mn, "max": mx, "pp": mx - mn,
            "dc": float(np.mean(arr)), "rms": rms, "sigma": sigma,
            "peak_factor": (mx / rms) if rms > 0 else 0.0,
            "dominant_freq": 0.0,
        })

    return JSONResponse({
        "file": label,
        "fs_hz": float(fs),
        "n": int(len(times)),
        "times": times.tolist(),
        "channels": channels_out,
        "spectrum": {"freqs": spectrum_freqs or [], "amps": spectrum_amps},
        "histogram": {"edges": hist_edges or [], "counts": hist_counts},
    })


# ============================================================
# /api/plot/wave — PNG с осциллограммой
# ============================================================
@app.get("/api/plot/wave")
async def api_plot_wave(
    from_: Optional[str] = Query(None, alias="from"),
    to_:   Optional[str] = Query(None, alias="to"),
    xmin:  Optional[float] = None,
    xmax:  Optional[float] = None,
    ymin:  Optional[float] = None,
    ymax:  Optional[float] = None,
    hidden: Optional[str] = None,   # "ch1,ch3" — скрытые каналы
):
    times, chans, label = _get_data_for_range(from_, to_, 500000)
    if times is None or len(times) < 2:
        return JSONResponse({"error": "no data"}, status_code=404)

    # Фильтруем скрытые каналы
    if hidden:
        hide = set(h.strip().lower() for h in hidden.split(",") if h.strip())
        chans = {k: v for k, v in chans.items() if k.lower() not in hide}
        if not chans:
            return JSONResponse({"error": "all channels hidden"}, status_code=400)

    xlim = (xmin, xmax) if xmin is not None and xmax is not None else None
    ylim = (ymin, ymax) if ymin is not None and ymax is not None else None

    png = plot.plot_wave(times, chans, xlim=xlim, ylim=ylim)

    resp = Response(content=png, media_type="image/png")
    resp.headers["X-Points"] = str(len(times))
    resp.headers["X-Label"] = label or ""

    if xlim is not None:
        resp.headers["X-XLim"] = f"{xlim[0]},{xlim[1]}"
    else:
        resp.headers["X-XLim"] = f"{float(times[0])},{float(times[-1])}"

    if ylim is not None:
        resp.headers["X-YLim"] = f"{ylim[0]},{ylim[1]}"
    else:
        all_vals = np.concatenate([np.asarray(a) for a in chans.values()])
        resp.headers["X-YLim"] = f"{float(np.min(all_vals))},{float(np.max(all_vals))}"

    # CORS-заголовки, чтобы JS мог читать их через fetch
    resp.headers["Access-Control-Expose-Headers"] = "X-Points,X-Label,X-XLim,X-YLim"
    return resp


# ============================================================
# /api/plot/fft — PNG со спектром
# ============================================================
@app.get("/api/plot/fft")
async def api_plot_fft(
    from_: Optional[str] = Query(None, alias="from"),
    to_:   Optional[str] = Query(None, alias="to"),
    fmin:  Optional[float] = None,
    fmax:  Optional[float] = None,
):
    times, chans, label = _get_data_for_range(from_, to_, 100000)
    if times is None or len(times) < 16:
        return JSONResponse({"error": "no data"}, status_code=404)

    dt = float(np.mean(np.diff(times)))
    fs = 1.0 / dt if dt > 0 else 14000.0

    N_FFT = min(16384, len(times))
    freqs_out = None
    amps = {}
    for name, arr in chans.items():
        arr = np.asarray(arr, dtype=float)
        seg = arr[-N_FFT:]
        win = np.hanning(len(seg))
        seg_w = (seg - np.mean(seg)) * win
        fft_vals = np.fft.rfft(seg_w)
        f = np.fft.rfftfreq(len(seg), d=1.0 / fs)
        a = np.abs(fft_vals) * 2.0 / np.sum(win)
        if len(a) > 0:
            a[0] /= 2.0
        freqs_out = f
        amps[name] = a

    xlim = (fmin, fmax) if fmin is not None and fmax is not None else None
    png = plot.plot_fft(freqs_out, amps, xlim=xlim)
    return Response(content=png, media_type="image/png")


# ============================================================
# /api/plot/hist — PNG с гистограммой
# ============================================================
@app.get("/api/plot/hist")
async def api_plot_hist(
    from_: Optional[str] = Query(None, alias="from"),
    to_:   Optional[str] = Query(None, alias="to"),
    ch:    int = 0,
    bins:  int = 25,
):
    times, chans, label = _get_data_for_range(from_, to_, 500000)
    if times is None or not chans:
        return JSONResponse({"error": "no data"}, status_code=404)

    names = list(chans.keys())
    if ch < 0 or ch >= len(names):
        ch = 0
    name = names[ch]
    arr = chans[name]

    counts, edges = np.histogram(arr, bins=bins)
    png = plot.plot_hist(counts, edges, channel_name=name)
    return Response(content=png, media_type="image/png")


# ============================================================
# /api/plot/stats — PNG с таблицей статистики
# ============================================================
@app.get("/api/plot/stats")
async def api_plot_stats(
    from_: Optional[str] = Query(None, alias="from"),
    to_:   Optional[str] = Query(None, alias="to"),
):
    times, chans, label = _get_data_for_range(from_, to_, 500000)
    if times is None or not chans:
        return JSONResponse({"error": "no data"}, status_code=404)

    # fs для доминирующей частоты
    dt = float(np.mean(np.diff(times)))
    fs = 1.0 / dt if dt > 0 else 14000.0

    stats = []
    for name, arr in chans.items():
        arr = np.asarray(arr, dtype=float)
        mn, mx = float(np.min(arr)), float(np.max(arr))
        rms = float(np.sqrt(np.mean(arr * arr)))

        # Доминирующая частота
        N_FFT = min(16384, len(arr))
        seg = arr[-N_FFT:]
        win = np.hanning(len(seg))
        seg_w = (seg - np.mean(seg)) * win
        fft_vals = np.fft.rfft(seg_w)
        freqs = np.fft.rfftfreq(len(seg), d=1.0 / fs)
        amps = np.abs(fft_vals)
        if len(amps) > 1:
            dom_idx = int(np.argmax(amps[1:])) + 1
            dom_freq = float(freqs[dom_idx])
        else:
            dom_freq = 0.0

        stats.append({
            'name': name,
            'min': mn,
            'max': mx,
            'pp': mx - mn,
            'dc': float(np.mean(arr)),
            'rms': rms,
            'sigma': float(np.std(arr)),
            'peak_factor': (mx / rms) if rms > 0 else 0.0,
            'dominant_freq': dom_freq,
        })

    png = plot.plot_stats_table(stats)
    return Response(content=png, media_type="image/png")

@app.get("/api/ltrd/reset")
async def api_ltrd_reset(slot: int = 1, csn: str = ""):
    params = {"slot": str(slot)}
    if csn:
        params["csn"] = csn
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            r = await client.get(f"{CPP_URL}/api/ltrd/reset", params=params)
            return JSONResponse(r.json(), status_code=r.status_code)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=503)

# ============================================================
# Запуск
# ============================================================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)