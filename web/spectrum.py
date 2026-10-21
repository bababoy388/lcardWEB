#!/usr/bin/env python3
"""
Расчёт спектра (FFT) по CSV-файлу с данными LTR24.

Формат входного CSV: time,ch1,ch2,...
Формат выходного CSV: freq_hz,amp_ch1,amp_ch2,...
"""

import os
import sys
import glob
import csv
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.widgets import SpanSelector


# ============================================================
# Параметры по умолчанию
# ============================================================
FS_DEFAULT = 14000.0        # частота дискретизации, Гц
OUTPUT_SUFFIX = "_spectrum" # суффикс выходного файла
WINDOW = "hann"             # окно: "hann", "hamming", "blackman", "none"
DETREND = True              # вычитать постоянную составляющую


# ============================================================
# Выбор файла
# ============================================================
def pick_file(folder="."):
    """Показывает список CSV-файлов в папке и предлагает выбрать."""
    files = sorted(glob.glob(os.path.join(folder, "*.csv")))
    # Исключаем уже обработанные спектры
    files = [f for f in files if not f.endswith(f"{OUTPUT_SUFFIX}.csv")]

    if not files:
        print(f"В папке {folder} нет CSV-файлов.")
        sys.exit(1)

    print("\nДоступные файлы:")
    for i, f in enumerate(files):
        size = os.path.getsize(f)
        print(f"  [{i}] {os.path.basename(f)}  ({size} байт)")

    print()
    while True:
        try:
            choice = input("Выберите номер файла (Enter — последний): ").strip()
            if choice == "":
                idx = len(files) - 1
            else:
                idx = int(choice)
            if 0 <= idx < len(files):
                return files[idx]
            print("Неверный номер, попробуйте снова.")
        except (ValueError, KeyboardInterrupt):
            print("Введите число.")


# ============================================================
# Чтение CSV
# ============================================================
def load_csv(path):
    """Возвращает (time, {name: array})."""
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader)
        if not header or header[0].lower() != "time":
            raise ValueError("Первая колонка должна быть 'time'")

        channel_names = header[1:]
        columns = [[] for _ in header]

        for row in reader:
            if not row:
                continue
            for i, val in enumerate(row):
                if i < len(columns):
                    try:
                        columns[i].append(float(val))
                    except ValueError:
                        columns[i].append(np.nan)

    time = np.array(columns[0])
    channels = {name: np.array(columns[i + 1])
                for i, name in enumerate(channel_names)}
    return time, channels


# ============================================================
# Оценка частоты дискретизации
# ============================================================
def estimate_fs(time):
    """Оценивает fs по среднему шагу между отсчётами."""
    if len(time) < 2:
        return FS_DEFAULT
    dt = np.mean(np.diff(time))
    if dt <= 0:
        return FS_DEFAULT
    return 1.0 / dt


# ============================================================
# Расчёт спектра
# ============================================================
def compute_spectrum(signal, fs, window=WINDOW, detrend=DETREND):
    """Возвращает (freqs, amplitude)."""
    signal = np.asarray(signal, dtype=float)

    # Убираем NaN
    if np.isnan(signal).any():
        signal = np.nan_to_num(signal, nan=0.0)

    N = len(signal)
    if N < 4:
        raise ValueError("Слишком мало точек для FFT")

    # Постоянная составляющая
    if detrend:
        signal = signal - np.mean(signal)

    # Окно
    if window == "hann":
        w = np.hanning(N)
    elif window == "hamming":
        w = np.hamming(N)
    elif window == "blackman":
        w = np.blackman(N)
    elif window == "none":
        w = np.ones(N)
    else:
        raise ValueError(f"Неизвестное окно: {window}")

    signal = signal * w

    # FFT
    fft_vals = np.fft.rfft(signal)
    freqs = np.fft.rfftfreq(N, d=1.0 / fs)

    # Амплитуда с учётом окна
    # (умножаем на 2 для одностороннего спектра; делим на сумму окна)
    amp = np.abs(fft_vals) * 2.0 / np.sum(w)
    amp[0] = np.abs(fft_vals[0]) / np.sum(w)   # DC не удваиваем

    return freqs, amp


# ============================================================
# Сохранение спектра
# ============================================================
def save_spectrum(path, freqs, spectra):
    """
    spectra: dict {name: array_amplitude}
    """
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["freq_hz"] + list(spectra.keys()))
        for i in range(len(freqs)):
            row = [f"{freqs[i]:.6f}"]
            for name in spectra:
                row.append(f"{spectra[name][i]:.9e}")
            w.writerow(row)
    print(f"Спектр сохранён: {path}")


# ============================================================
# График
# ============================================================
def plot_spectrum(freqs, spectra, title, max_freq=None):
    fig, ax = plt.subplots(figsize=(12, 6))

    colors = ["#e74c3c", "#3498db", "#2ecc71", "#f39c12"]
    for i, (name, amp) in enumerate(spectra.items()):
        ax.plot(freqs, amp, label=name,
                color=colors[i % len(colors)], linewidth=0.8)

    ax.set_xlabel("Частота, Гц")
    ax.set_ylabel("Амплитуда, В")
    ax.set_title(title)
    ax.grid(True, alpha=0.3)
    ax.legend()

    if max_freq is not None:
        ax.set_xlim(0, max_freq)

    plt.tight_layout()
    return fig, ax


# ============================================================
# main
# ============================================================
def main():
    print("=" * 60)
    print("Расчёт спектра по файлу данных LTR24")
    print("=" * 60)

    # 1. Выбор файла
    folder = sys.argv[1] if len(sys.argv) > 1 else "."
    input_path = pick_file(folder)

    # 2. Чтение
    print(f"\nЧитаем: {input_path}")
    time, channels = load_csv(input_path)
    N = len(time)
    print(f"  Точек: {N}")
    print(f"  Каналов: {list(channels.keys())}")

    # 3. Оценка fs
    fs = estimate_fs(time)
    print(f"  Оценка fs: {fs:.3f} Гц")

    if len(time) > 1:
        duration = time[-1] - time[0]
        print(f"  Длительность: {duration:.6f} с "
              f"({duration*1000:.3f} мс)")
        print(f"  Разрешение по частоте: {fs/N:.3f} Гц")
        print(f"  Частота Найквиста: {fs/2:.1f} Гц")

    # 4. Расчёт спектра для каждого канала
    spectra = {}
    freqs = None
    for name, sig in channels.items():
        print(f"  FFT для {name}...")
        fr, amp = compute_spectrum(sig, fs, WINDOW, DETREND)
        freqs = fr
        spectra[name] = amp

    # 5. Сохранение
    base, ext = os.path.splitext(input_path)
    output_path = f"{base}{OUTPUT_SUFFIX}{ext}"
    save_spectrum(output_path, freqs, spectra)

    # 6. График
    title = f"Спектр: {os.path.basename(input_path)}  (fs={fs:.1f} Гц)"
    plot_spectrum(freqs, spectra, title)
    plt.show()


if __name__ == "__main__":
    main()