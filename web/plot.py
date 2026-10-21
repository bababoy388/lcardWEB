"""
Генерация графиков через matplotlib (Agg-бэкенд, без GUI).
Все функции возвращают PNG в виде байтов.
"""
import io
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.ticker import MaxNLocator


# ============================================================
# Тёмная тема под стиль проекта
# ============================================================
plt.rcParams.update({
    'figure.facecolor':    '#161b22',
    'figure.edgecolor':    '#161b22',
    'axes.facecolor':      '#0f141b',
    'axes.edgecolor':      '#2a323d',
    'axes.labelcolor':     '#e6edf3',
    'axes.titlecolor':     '#e6edf3',
    'axes.linewidth':      0.8,
    'xtick.color':         '#8b949e',
    'ytick.color':         '#8b949e',
    'xtick.labelsize':     9,
    'ytick.labelsize':     9,
    'grid.color':          '#1e242c',
    'grid.linewidth':      0.6,
    'text.color':          '#e6edf3',
    'font.family':         'monospace',
    'font.size':           9,
    'legend.frameon':      False,
    'legend.fontsize':     8,
    'path.simplify':       True,
    'path.simplify_threshold': 0.5,
    'agg.path.chunksize':  10000,
})

CH_COLORS = {
    'ch1': '#e8b631',
    'ch2': '#4ecdc4',
    'ch3': '#e91e63',
    'ch4': '#4caf50',
}


def _to_png(fig, dpi=110):
    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=dpi,
                bbox_inches='tight', pad_inches=0.2)
    plt.close(fig)
    buf.seek(0)
    return buf.read()


# ============================================================
# Осциллограмма
# ============================================================
def plot_wave(times, channels, xlim=None, ylim=None, width_in=12, height_in=3.2):
    """
    times    — np.array (сек), можно datetime64
    channels — dict {name: np.array}
    xlim     — (xmin, xmax) или None (авто)
    ylim     — (ymin, ymax) или None (авто)
    """
    fig, ax = plt.subplots(figsize=(width_in, height_in))

    for name, arr in channels.items():
        color = CH_COLORS.get(name.lower(), '#8b949e')
        ax.plot(times, arr, color=color, linewidth=0.7,
                label=name.upper(), antialiased=True)

    ax.grid(True, alpha=0.35, linestyle='-')
    ax.set_xlabel('Время, с')
    ax.set_ylabel('Напряжение, В')
    if channels:
        ax.legend(loc='upper right', ncol=min(4, len(channels)))

    if xlim is not None:
        ax.set_xlim(*xlim)
    if ylim is not None:
        ax.set_ylim(*ylim)

    return _to_png(fig)


# ============================================================
# Спектр FFT
# ============================================================
def plot_fft(freqs, amps_dict, xlim=None, log_x=True,
             width_in=6, height_in=3):
    """
    freqs     — np.array, Гц
    amps_dict — dict {name: np.array амплитуд}
    log_x     — логарифмическая шкала по X
    """
    fig, ax = plt.subplots(figsize=(width_in, height_in))

    for i, (name, arr) in enumerate(amps_dict.items()):
        color = CH_COLORS.get(name.lower(), list(CH_COLORS.values())[i % 4])
        ax.semilogy(freqs, arr, color=color, linewidth=0.8,
                    label=name.upper())

    if log_x:
        ax.set_xscale('log')
        # Исключаем 0 (log не любит)
        if xlim is not None:
            xmin = max(xlim[0], 1.0)
            ax.set_xlim(xmin, xlim[1])

    ax.grid(True, alpha=0.35, which='both')
    ax.set_xlabel('Частота, Гц')
    ax.set_ylabel('Амплитуда, В')
    ax.legend(loc='upper right')

    return _to_png(fig)


# ============================================================
# Гистограмма
# ============================================================
def plot_hist(counts, edges, channel_name='CH1',
              width_in=6, height_in=3):
    fig, ax = plt.subplots(figsize=(width_in, height_in))

    widths = np.diff(edges)
    centers = edges[:-1] + widths / 2
    color = CH_COLORS.get(channel_name.lower(), '#e8b631')
    ax.bar(centers, counts, width=widths * 0.92,
           color=color, edgecolor='none', alpha=0.9)

    ax.grid(True, alpha=0.35)
    ax.set_xlabel('Напряжение, В')
    ax.set_ylabel('Количество')
    ax.set_title(channel_name.upper())
    ax.yaxis.set_major_locator(MaxNLocator(nbins=5, integer=True))

    return _to_png(fig)


# ============================================================
# Статистика (таблица-картинка, опционально)
# ============================================================
def plot_stats_table(channels):
    """
    channels — список dict с полями:
      name, min, max, pp, dc, rms, sigma, peak_factor, dominant_freq
    Рисует таблицу-картинку.
    """
    cols = ['Канал', 'Мин, В', 'Макс, В', 'Pk-Pk, В',
            'DC, В', 'RMS, В', 'σ, В', 'Пик-фактор', 'Дом.частота, Гц']

    rows = []
    for ch in channels:
        rows.append([
            ch['name'].upper(),
            f"{ch['min']:.3f}",
            f"{ch['max']:.3f}",
            f"{ch['pp']:.3f}",
            f"{ch['dc']:.3f}",
            f"{ch['rms']:.3f}",
            f"{ch['sigma']:.3f}",
            f"{ch['peak_factor']:.3f}",
            f"{ch['dominant_freq']:.1f}",
        ])

    fig, ax = plt.subplots(figsize=(12, 0.5 + 0.4 * len(rows)))
    ax.axis('off')

    table = ax.table(
        cellText=rows,
        colLabels=cols,
        cellLoc='center',
        loc='center',
    )
    table.auto_set_font_size(False)
    table.set_fontsize(9)
    table.scale(1, 1.4)

    # Стили
    for (row, col), cell in table.get_celld().items():
        cell.set_edgecolor('#2a323d')
        if row == 0:
            cell.set_facecolor('#1c2128')
            cell.set_text_props(color='#8b949e', weight='bold')
        else:
            cell.set_facecolor('#161b22')
            ch_name = rows[row - 1][0].lower()
            cell.set_text_props(color=CH_COLORS.get(ch_name, '#e6edf3'))

    return _to_png(fig)