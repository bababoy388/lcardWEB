// ============================================================
// Глобальное состояние
// ============================================================
let currentConfig = null;
let pollTimer = null;

// ============================================================
// Тема
// ============================================================
function toggleTheme() {
  const html = document.documentElement;
  const cur = html.getAttribute('data-theme');
  html.setAttribute('data-theme', cur === 'dark' ? 'light' : 'dark');
}

// ============================================================
// API-хелперы
// ============================================================
async function apiGet(path) {
  const r = await fetch(path);
  if (!r.ok) throw new Error(`GET ${path}: ${r.status}`);
  return r.json();
}

async function apiPost(path, body) {
  const r = await fetch(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!r.ok) throw new Error(`POST ${path}: ${r.status}`);
  return r.json();
}

async function apiAction(path) {
  // GET-вариант для /start и /stop (шлём простой GET)
  const r = await fetch(path);
  if (!r.ok) throw new Error(`GET ${path}: ${r.status}`);
  return r.json();
}

// ============================================================
// Загрузка конфига с сервера → заполнение формы
// ============================================================
async function loadConfig() {
  try {
    const cfg = await apiGet('/api/config');
    currentConfig = cfg;

    // Частота
    document.getElementById('selFreq').value = cfg.freq_hz;
    // Формат
    document.getElementById('selFormat').value = cfg.format;
    // Цикл
    document.getElementById('inpRecord').value = cfg.record_time;
    document.getElementById('inpSleep').value  = cfg.sleep_time;
    // Шаблон файла — восстанавливаем "run_{date}_{time}.csv" из "run.csv"
    document.getElementById('inpFileTemplate').value = restoreTemplate(cfg.output_file);

    // Каналы
    cfg.channels.forEach((ch, i) => {
      const en  = document.querySelector(`.ch-enable[data-ch="${i}"]`);
      const ac  = document.querySelector(`.ch-ac[data-ch="${i}"]`);
      const icp = document.querySelector(`.ch-icp[data-ch="${i}"]`);
      if (en)  en.checked  = !!ch.enable;
      if (ac)  ac.checked  = !!ch.ac;
      if (icp) icp.checked = !!ch.icp;

      // Диапазон
      const group = document.querySelector(`.toggle-group[data-ch="${i}"]`);
      if (group) {
        group.querySelectorAll('.tg').forEach(btn => {
          btn.classList.toggle('active', parseInt(btn.dataset.range) === ch.range);
        });
      }
    });

    updateSummary();
    console.log('[CFG] загружено:', cfg);
  } catch (e) {
    console.error('[CFG] ошибка загрузки:', e);
    showToast('Не удалось загрузить конфигурацию: ' + e.message, 'error');
  }
}

// ============================================================
// Сборка конфига из формы → отправка на сервер
// ============================================================
function collectConfig() {
  const payload = {
    freq_hz:     parseInt(document.getElementById('selFreq').value),
    format:      parseInt(document.getElementById('selFormat').value),
    record_time: parseFloat(document.getElementById('inpRecord').value),
    sleep_time:  parseFloat(document.getElementById('inpSleep').value),
    output_file: normalizeTemplate(document.getElementById('inpFileTemplate').value),
    write_to_file: true,
  };

  for (let i = 0; i < 4; i++) {
    const en  = document.querySelector(`.ch-enable[data-ch="${i}"]`).checked;
    const ac  = document.querySelector(`.ch-ac[data-ch="${i}"]`).checked;
    const icp = document.querySelector(`.ch-icp[data-ch="${i}"]`).checked;
    const rangeBtn = document.querySelector(`.toggle-group[data-ch="${i}"] .tg.active`);
    const range = rangeBtn ? parseInt(rangeBtn.dataset.range) : 2;

    payload[`ch${i}_enable`] = en;
    payload[`ch${i}_ac`]     = ac;
    payload[`ch${i}_icp`]    = icp;
    payload[`ch${i}_range`]  = range;
  }

  return payload;
}

// ============================================================
// Преобразование шаблона имени файла
// ============================================================
// "run_{date}_{time}.csv" → "run.csv" (базовое имя для C++)
function normalizeTemplate(tpl) {
  if (!tpl) return 'data.csv';
  let base = tpl
    .replace(/\.csv$/i, '')
    .replace(/[_\-]?\{date\}/gi, '')
    .replace(/[_\-]?\{time\}/gi, '')
    .trim();
  if (!base) base = 'data';
  return base + '.csv';
}

// "run.csv" → "run_{date}_{time}.csv" (обратно в UI)
function restoreTemplate(base) {
  if (!base) return 'run_{date}_{time}.csv';
  let name = base.replace(/\.csv$/i, '');
  // Убираем автоматически добавленный хвост _YYYYMMDD_HHMMSS
  name = name.replace(/_\d{8}_\d{6}$/,'');
  return name + '_{date}_{time}.csv';
}

// ============================================================
// Кнопки
// ============================================================
async function onSave() {
  const payload = collectConfig();
  console.log('[SAVE] отправляю:', payload);

  const saveBtn = document.querySelector('.footer-actions .btn-primary');
  if (saveBtn) saveBtn.disabled = true;

  try {
    const res = await apiPost('/api/config', payload);
    console.log('[SAVE] ответ:', res);

    if (res.saved === false) {
      showToast('Не удалось сохранить конфиг', 'error');
      return;
    }

    showToast('Сохранено. L-Card перезапускается…', 'success');

    // C++ завершится и сам запустит себя заново.
    // Периодически проверяем, ожил ли он.
    waitForRestart(3000);

  } catch (e) {
    showToast('Ошибка сохранения: ' + e.message, 'error');
  } finally {
    if (saveBtn) saveBtn.disabled = false;
  }
}

async function waitForRestart(initialDelayMs) {
  // Сначала ждём, пока старый процесс точно завершится
  await new Promise(r => setTimeout(r, initialDelayMs));

  // Потом пробуем достучаться до C++ раз в секунду
  let attempts = 0;
  const maxAttempts = 15;

  const timer = setInterval(async () => {
    attempts++;
    try {
      const cfg = await apiGet('/api/config');
      currentConfig = cfg;
      updateSummary();
      clearInterval(timer);
      showToast('L-Card перезапущен, настройки применены', 'success');
      console.log('[RESTART] OK через', attempts, 'сек');
    } catch (_) {
      if (attempts >= maxAttempts) {
        clearInterval(timer);
        showToast('L-Card не отвечает. Проверьте консоль', 'error');
      }
    }
  }, 1000);
}

async function onStart() {
  try {
    const res = await apiAction('/api/start');
    console.log('[START]', res);
    showToast('Запись запущена', 'success');
    startPolling();
  } catch (e) {
    showToast('Ошибка запуска: ' + e.message, 'error');
  }
}

async function onStop() {
  try {
    const res = await apiAction('/api/stop');
    console.log('[STOP]', res);
    showToast('Запись остановлена', 'success');
    stopPolling();
  } catch (e) {
    showToast('Ошибка остановки: ' + e.message, 'error');
  }
}

function onReset() {
  if (!confirm('Сбросить все изменения формы?')) return;
  loadConfig();
  showToast('Форма сброшена к серверным значениям', 'success');
}

// ============================================================
// Сводка справа
// ============================================================
function updateSummary() {
  const enabled = [];
  document.querySelectorAll('.ch-enable').forEach(cb => {
    if (cb.checked) enabled.push('CH' + (parseInt(cb.dataset.ch) + 1));
  });
  document.getElementById('sumChannels').textContent =
    enabled.length ? enabled.join(', ') : '—';

  const tag = document.getElementById('chCount');
  if (tag) tag.textContent = `${enabled.length} ${plural(enabled.length, 'канал', 'канала', 'каналов')} выбрано`;

  let range = '—';
  const firstActive = document.querySelector('.toggle-group .tg.active');
  if (firstActive) range = '±' + firstActive.dataset.range + ' В';
  document.getElementById('sumRange').textContent = range;

  const acOn = document.querySelectorAll('.ch-ac:checked').length > 0;
  const icpOn = document.querySelectorAll('.ch-icp:checked').length > 0;
  document.getElementById('sumAc').textContent =
    (acOn ? 'Вкл.' : 'Выкл.') + ' / ' + (icpOn ? 'Вкл.' : 'Выкл.');

  const rec   = document.getElementById('inpRecord').value || '0';
  const sleep = document.getElementById('inpSleep').value || '0';
  document.getElementById('sumCycle').textContent = `${rec}с / ${sleep}с`;

  const freq = document.getElementById('selFreq').value;
  document.getElementById('sumFreq').textContent =
    Number(freq).toLocaleString('ru-RU') + ' Гц';

  const fmt = document.getElementById('selFormat').value;
  document.getElementById('sumFormat').textContent = fmt + ' бит';

  const tpl = document.getElementById('inpFileTemplate').value;
  document.getElementById('sumFile').textContent = tpl || '—';
}

function plural(n, one, few, many) {
  const m10 = n % 10, m100 = n % 100;
  if (m10 === 1 && m100 !== 11) return one;
  if (m10 >= 2 && m10 <= 4 && (m100 < 10 || m100 >= 20)) return few;
  return many;
}

// ============================================================
// Поллинг статуса (пока запущено)
// ============================================================
async function pollStatus() {
  try {
    const s = await apiGet('/api/status');
    const phaseEl = document.querySelector('.status-phase');
    if (phaseEl) phaseEl.textContent = s.phase || 'idle';

    // Блокируем/разблокируем кнопки в соответствии с фазой
    const running = !!s.running;
    const btnStart = document.getElementById('btnStart');
    const btnStop  = document.getElementById('btnStop');
    if (btnStart) btnStart.classList.toggle('locked', running);
    if (btnStop)  btnStop.disabled = !running;
  } catch (e) {
    // C++ недоступен — просто выходим
  }
}

function startPolling() {
  if (pollTimer) return;
  pollTimer = setInterval(pollStatus, 1000);
  pollStatus();
}
function stopPolling() {
  if (pollTimer) {
    clearInterval(pollTimer);
    pollTimer = null;
  }
}

// ============================================================
// Uptime в шапке
// ============================================================
function startUptime() {
  let seconds = 12 * 60 + 48;
  setInterval(() => {
    seconds++;
    const hh = String(Math.floor(seconds / 3600)).padStart(2, '0');
    const mm = String(Math.floor((seconds % 3600) / 60)).padStart(2, '0');
    const ss = String(seconds % 60).padStart(2, '0');
    const el = document.getElementById('uptime');
    if (el) el.textContent = `${hh}:${mm}:${ss}`;
  }, 1000);
}

// ============================================================
// Тост-уведомление
// ============================================================
function showToast(msg, kind = 'info') {
  let box = document.getElementById('toast');
  if (!box) {
    box = document.createElement('div');
    box.id = 'toast';
    box.className = 'toast';
    document.body.appendChild(box);
  }
  box.textContent = msg;
  box.className = 'toast ' + kind + ' show';
  clearTimeout(box._t);
  box._t = setTimeout(() => box.classList.remove('show'), 2500);
}

// ============================================================
// Обработчики
// ============================================================
document.addEventListener('DOMContentLoaded', async () => {
  // Чекбоксы и поля — пересчитываем сводку
  document.querySelectorAll('.ch-enable, .ch-ac, .ch-icp').forEach(cb => {
    cb.addEventListener('change', updateSummary);
  });
  ['inpRecord', 'inpSleep'].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.addEventListener('input', updateSummary);
  });
  ['selFreq', 'selFormat'].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.addEventListener('change', updateSummary);
  });
  document.getElementById('inpFileTemplate')
    ?.addEventListener('input', updateSummary);

  // Переключатели ±2/±10 В
  document.querySelectorAll('.toggle-group').forEach(group => {
    group.querySelectorAll('.tg').forEach(btn => {
      btn.addEventListener('click', () => {
        group.querySelectorAll('.tg').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        updateSummary();
      });
    });
  });

  // Загружаем конфиг с сервера
  await loadConfig();
  startUptime();
  startPolling();
});