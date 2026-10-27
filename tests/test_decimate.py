"""
Тест scipy.signal.decimate.

Демонстрирует три вещи:
1. Как выглядит исходный сигнал при fs = 14000 Гц.
2. Как работает decimate с фильтром (правильно).
3. Что будет при "наивном" прореживании без фильтра (алиасинг).
"""

import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import decimate, welch

# ============================================================
# 1. Параметры сигнала
# ============================================================
fs_high = 14000.0          # исходная частота дискретизации, Гц
T = 1.0                    # длительность записи, сек
N_high = int(fs_high * T)  # количество точек

t = np.arange(N_high) / fs_high  # временная ось

# ============================================================
# 2. Модель сигнала: смесь полезных частот
# ============================================================
# - 50 Гц — наводка сети (очень большая)
# - 500 Гц — "полезная" вибрация
# - 3000 Гц — ещё одна полезная компонента
# - 6500 Гц — высокочастотная компонента (близко к Найквисту 7000)
signal = (
    1.0 * np.sin(2 * np.pi * 50 * t)     # наводка 50 Гц
    + 0.5 * np.sin(2 * np.pi * 500 * t)  # полезный сигнал 500 Гц
    + 0.3 * np.sin(2 * np.pi * 3000 * t) # ещё один полезный сигнал
    + 0.2 * np.sin(2 * np.pi * 6500 * t) # высокочастотная компонента
)

# Немного шума, чтобы было реалистично
rng = np.random.default_rng(42)
signal += rng.normal(0, 0.02, size=signal.shape)

print(f"Исходный сигнал: {len(signal)} точек, fs = {fs_high} Гц, T = {T} сек")
print(f"Частота Найквиста: {fs_high/2} Гц")

# ============================================================
# 3. Децимация с фильтром (правильный способ)
# ============================================================
q = 10                     # коэффициент децимации (в 10 раз)
fs_low = fs_high / q       # новая частота дискретизации
print(f"\nДецимация в {q} раз: fs_low = {fs_low} Гц, Nyquist = {fs_low/2} Гц")

signal_dec = decimate(signal, q=q, ftype='fir', zero_phase=True)
t_dec = np.arange(len(signal_dec)) / fs_low

print(f"После decimate: {len(signal_dec)} точек")

# ============================================================
# 4. "Наивное" прореживание без фильтра (для сравнения)
# ============================================================
signal_naive = signal[::q]   # просто берём каждый q-й отсчёт
print(f"После naive slicing: {len(signal_naive)} точек")

# ============================================================
# 5. График: временная область
# ============================================================
fig, axes = plt.subplots(3, 2, figsize=(14, 9))
fig.suptitle("Тест scipy.signal.decimate: fs = 14000 → 1400 Гц", fontsize=14)

# --- 5.1. Исходный сигнал (первые 100 мс) ---
ax = axes[0, 0]
n_show = int(0.1 * fs_high)
ax.plot(t[:n_show]*1000, signal[:n_show], color="#e8b631", linewidth=0.8)
ax.set_title(f"Исходный сигнал (fs = {fs_high:.0f} Гц)")
ax.set_xlabel("Время, мс")
ax.set_ylabel("Амплитуда")
ax.grid(True, alpha=0.3)

# --- 5.2. После decimate (первые 100 мс) ---
ax = axes[0, 1]
n_show_dec = int(0.1 * fs_low)
ax.plot(t_dec[:n_show_dec]*1000, signal_dec[:n_show_dec],
        color="#4ecdc4", linewidth=0.8, marker='.', markersize=2)
ax.set_title(f"После decimate с фильтром (fs = {fs_low:.0f} Гц)")
ax.set_xlabel("Время, мс")
ax.grid(True, alpha=0.3)

# --- 5.3. Спектр исходного сигнала ---
ax = axes[1, 0]
f_orig, P_orig = welch(signal, fs=fs_high, nperseg=4096)
ax.semilogy(f_orig, P_orig, color="#e8b631", linewidth=0.8)
ax.set_title("Спектр исходного сигнала")
ax.set_xlabel("Частота, Гц")
ax.set_ylabel("Мощность")
ax.set_xlim(0, fs_high / 2)
ax.grid(True, alpha=0.3, which='both')

# Отметим пики
for f_peak in [50, 500, 3000, 6500]:
    ax.axvline(f_peak, color='red', linestyle='--', alpha=0.3, linewidth=0.7)
    ax.text(f_peak, ax.get_ylim()[1] * 0.3, f"{f_peak}",
            fontsize=8, color='red', ha='center')

# --- 5.4. Спектр после decimate ---
ax = axes[1, 1]
f_dec, P_dec = welch(signal_dec, fs=fs_low, nperseg=1024)
ax.semilogy(f_dec, P_dec, color="#4ecdc4", linewidth=0.8)
ax.set_title(f"Спектр после decimate (fs = {fs_low:.0f} Гц)")
ax.set_xlabel("Частота, Гц")
ax.set_xlim(0, fs_low / 2)
ax.grid(True, alpha=0.3, which='both')

for f_peak in [50, 500]:
    ax.axvline(f_peak, color='red', linestyle='--', alpha=0.3, linewidth=0.7)
    ax.text(f_peak, ax.get_ylim()[1] * 0.3, f"{f_peak}",
            fontsize=8, color='red', ha='center')

# --- 5.5. Спектр "наивного" прореживания (виден алиасинг) ---
ax = axes[2, 0]
f_nv, P_nv = welch(signal_naive, fs=fs_low, nperseg=1024)
ax.semilogy(f_nv, P_nv, color="#f85149", linewidth=0.8)
ax.set_title("Спектр после naive slicing (без фильтра!)")
ax.set_xlabel("Частота, Гц")
ax.set_xlim(0, fs_low / 2)
ax.grid(True, alpha=0.3, which='both')

# Отметим "фантомные" пики — результат алиасинга
# 3000 Гц завернётся: 1400 - (3000 % 1400) = 1400 - 200 = 1200 Гц
# 6500 Гц завернётся: 6500 % 1400 = 900 Гц
for f_alias, label in [(1200, "алиас 3000 Гц"), (900, "алиас 6500 Гц")]:
    ax.axvline(f_alias, color='orange', linestyle=':', alpha=0.7, linewidth=1)
    ax.text(f_alias, ax.get_ylim()[1] * 0.3, label,
            fontsize=8, color='orange', ha='center', rotation=90)

# --- 5.6. Сравнение спектров (наложение) ---
ax = axes[2, 1]
ax.semilogy(f_dec, P_dec, label="decimate (с фильтром)",
            color="#4ecdc4", linewidth=1)
ax.semilogy(f_nv, P_nv, label="naive slicing (без фильтра)",
            color="#f85149", linewidth=1, alpha=0.7)
ax.set_title("Сравнение: с фильтром vs без фильтра")
ax.set_xlabel("Частота, Гц")
ax.set_xlim(0, fs_low / 2)
ax.legend(fontsize=9)
ax.grid(True, alpha=0.3, which='both')

plt.tight_layout()
plt.savefig("decimate_test.png", dpi=120, bbox_inches='tight')
plt.show()

# ============================================================
# 6. Текстовый вывод: что где
# ============================================================
print("\n" + "="*60)
print("АНАЛИЗ РЕЗУЛЬТАТОВ")
print("="*60)
print(f"Исходные компоненты: 50, 500, 3000, 6500 Гц")
print(f"Новая частота Найквиста: {fs_low/2} Гц")
print()
print("После decimate (правильно):")
print(f"  - 50 Гц и 500 Гц должны быть на месте")
print(f"  - 3000 Гц и 6500 Гц должны быть подавлены")
print()
print("После naive slicing (алиасинг):")
print(f"  - 50 Гц и 500 Гц на месте")
print(f"  - 3000 Гц 'притворяется' пиком на {1400 - (3000 % 1400)} Гц")
print(f"  - 6500 Гц 'притворяется' пиком на {6500 % 1400} Гц")
print()
print("Откройте decimate_test.png — там всё наглядно.")