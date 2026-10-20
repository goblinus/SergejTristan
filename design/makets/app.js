'use strict';

/* ============================================================
   Дивидендный календарь — интерактивный прототип
   Данные демонстрационные, дата «сегодня» зафиксирована.
   ============================================================ */

const DEMO_TODAY = '2026-10-20';
const THRESHOLD_DAYS = 7;
const STORAGE_KEY = 'dvk.watchlist.v1';
const DEFAULT_WATCHLIST = ['SBER', 'GAZP', 'LKOH'];

const MONTHS = [
  'Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь',
  'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь'
];

const MEETINGS = [
  { id: 'm-mgnt', ticker: 'MGNT', issuer: 'Магнит', meeting: '2026-10-08', cutoff: '2026-10-05', agenda: 'выплачено 412 ₽', source: 'https://www.moex.com/ru/issue.aspx?code=MGNT', period: 'year', dps: 412, divYield: 12, dsi: 58 },
  { id: 'm-sngs', ticker: 'SNGS', issuer: 'Сургутнефтегаз', meeting: '2026-10-15', cutoff: '2026-10-12', agenda: 'выплачено 0,8 ₽', source: 'https://www.moex.com/ru/issue.aspx?code=SNGS', period: 'year', dps: 0.8, divYield: 2.1, dsi: 45 },
  { id: 'm-chmf', ticker: 'CHMF', issuer: 'Северсталь', meeting: '2026-10-22', cutoff: '2026-10-19', agenda: 'выплачено 121,8 ₽', source: 'https://www.moex.com/ru/issue.aspx?code=CHMF', period: 'quarter', dps: 121.8, divYield: 9.5, dsi: 83 },
  { id: 'm-mtss', ticker: 'MTSS', issuer: 'МТС', meeting: '2026-10-23', cutoff: '2026-10-20', agenda: 'в повестке', source: 'https://www.moex.com/ru/issue.aspx?code=MTSS', period: 'year', dps: 35, divYield: 12.5, dsi: 68 },
  { id: 'm-irao', ticker: 'IRAO', issuer: 'Интер РАО', meeting: '2026-10-26', cutoff: '2026-10-21', agenda: 'в повестке', source: 'https://www.moex.com/ru/issue.aspx?code=IRAO', period: 'year', dps: 0.5, divYield: 5, dsi: 52 },
  { id: 'm-plzl', ticker: 'PLZL', issuer: 'Полюс', meeting: '2026-10-27', cutoff: '2026-10-24', agenda: 'дивиденды рекомендованы', source: 'https://www.moex.com/ru/issue.aspx?code=PLZL', period: 'year', dps: 1300, divYield: 9.2, dsi: 74 },
  { id: 'm-moex', ticker: 'MOEX', issuer: 'Московская биржа', meeting: '2026-10-28', cutoff: '2026-10-23', agenda: 'дивиденды рекомендованы', source: 'https://www.moex.com/ru/issue.aspx?code=MOEX', period: 'quarter', dps: 26, divYield: 7.8, dsi: 85 },
  { id: 'm-aflt', ticker: 'AFLT', issuer: 'Аэрофлот', meeting: '2026-10-29', cutoff: '2026-10-26', agenda: 'решение совета директоров', source: 'https://www.moex.com/ru/issue.aspx?code=AFLT', period: 'year', dps: 5, divYield: 1.2, dsi: 35 },
  { id: 'm-phor', ticker: 'PHOR', issuer: 'ФосАгро', meeting: '2026-10-30', cutoff: '2026-10-27', agenda: 'в повестке', source: 'https://www.moex.com/ru/issue.aspx?code=PHOR', period: 'quarter', dps: 300, divYield: 8, dsi: 80 },
  { id: 'm-rosn', ticker: 'ROSN', issuer: 'Роснефть', meeting: '2026-11-05', cutoff: '2026-11-02', agenda: 'в повестке', source: 'https://www.moex.com/ru/issue.aspx?code=ROSN', period: 'half_year', dps: 30.5, divYield: 6, dsi: 71 },
  { id: 'm-sber', ticker: 'SBER', issuer: 'Сбербанк', meeting: '2026-11-12', cutoff: '2026-11-09', agenda: 'в повестке', source: 'https://www.moex.com/ru/issue.aspx?code=SBER', period: 'year', dps: 33.3, divYield: 8.4, dsi: 82 },
  { id: 'm-gazp', ticker: 'GAZP', issuer: 'Газпром', meeting: '2026-11-20', cutoff: '2026-11-16', agenda: 'в повестке', source: 'https://www.moex.com/ru/issue.aspx?code=GAZP', period: 'year', dps: 10, divYield: 6.1, dsi: 64 },
  { id: 'm-tatn', ticker: 'TATN', issuer: 'Татнефть', meeting: '2026-11-26', cutoff: '2026-11-23', agenda: 'дивиденды рекомендованы', source: 'https://www.moex.com/ru/issue.aspx?code=TATN', period: 'quarter', dps: 25, divYield: 6.5, dsi: 79 },
  { id: 'm-lkoh', ticker: 'LKOH', issuer: 'Лукойл', meeting: '2026-12-03', cutoff: '2026-11-30', agenda: 'дивиденды рекомендованы', source: 'https://www.moex.com/ru/issue.aspx?code=LKOH', period: 'year', dps: 498, divYield: 7.5, dsi: 88 },
  { id: 'm-nvtk', ticker: 'NVTK', issuer: 'НОВАТЭК', meeting: '2026-12-10', cutoff: '2026-12-07', agenda: 'в повестке', source: 'https://www.moex.com/ru/issue.aspx?code=NVTK', period: 'half_year', dps: 45, divYield: 5.8, dsi: 76 }
];

const TICKERS = Array.from(new Set(MEETINGS.map((m) => m.ticker)));

const ICONS = {
  close: '<path fill="currentColor" d="M19 6.41 17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/>',
  star: '<path fill="currentColor" d="m12 17.27 6.18 3.73-1.64-7.03L22 9.24l-7.19-.61L12 2 9.19 8.63 2 9.24l5.46 4.73L5.82 21z"/>',
  delete: '<path fill="currentColor" d="M6 19a2 2 0 0 0 2 2h8a2 2 0 0 0 2-2V7H6v12zM8 9h8v10H8V9zm7.5-5-1-1h-5l-1 1H5v2h14V4z"/>',
  arrow: '<path fill="currentColor" d="M6 6v2h8.59L5 17.59 6.41 19 16 9.41V18h2V6z"/>'
};

/* ---------- утилиты ---------- */

const $ = (selector, root = document) => root.querySelector(selector);
const $$ = (selector, root = document) => Array.from(root.querySelectorAll(selector));

function esc(value) {
  return String(value).replace(/[&<>"']/g, (ch) => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
  }[ch]));
}

function icon(name, className = '') {
  return `<svg class="icon ${className}" viewBox="0 0 24 24" aria-hidden="true" focusable="false">${ICONS[name]}</svg>`;
}

const DAY_MS = 86400000;

function toTs(isoDate) {
  const [year, month, day] = isoDate.split('-').map(Number);
  return Date.UTC(year, month - 1, day);
}

const TODAY_TS = toTs(DEMO_TODAY);

function daysUntil(isoDate) {
  return Math.round((toTs(isoDate) - TODAY_TS) / DAY_MS);
}

function fmtDate(isoDate) {
  const [year, month, day] = isoDate.split('-');
  return `${day}.${month}.${year}`;
}

function monthTitle(monthKey) {
  const [year, month] = monthKey.split('-').map(Number);
  return `${MONTHS[month - 1]} ${year}`;
}

function plural(number, forms) {
  const [one, few, many] = forms;
  const abs = Math.abs(number);
  const tail = abs % 100;
  if (tail >= 11 && tail <= 14) return many;
  const last = abs % 10;
  if (last === 1) return one;
  if (last >= 2 && last <= 4) return few;
  return many;
}

function daysLabel(days) {
  return `${days} ${plural(days, ['день', 'дня', 'дней'])}`;
}

function statusOf(meeting) {
  const days = daysUntil(meeting.cutoff);
  if (days < 0) return { key: 'past', days, label: 'Отсечка прошла' };
  if (days === 0) return { key: 'critical', days, label: 'Отсечка сегодня' };
  const label = `${daysLabel(days)} до отсечки`;
  return { key: days <= THRESHOLD_DAYS ? 'hot' : 'normal', days, label };
}

function shortStatus(status) {
  if (status.key === 'past') return 'прошла';
  if (status.key === 'critical') return 'сегодня';
  return daysLabel(status.days);
}

const PERIOD_LABELS = {
  year: 'год',
  half_year: 'полгода',
  quarter: 'квартал'
};

const DSI_HINT = 'DSI — индекс стабильности дивидендов, 0–100. Учитывает регулярность '
  + 'и изменчивость выплат за последние 5 лет: чем выше, тем стабильнее дивидендный поток. '
  + '80+ — высокая стабильность, 50–79 — средняя, ниже 50 — низкая.';

function fmtMoney(value) {
  return `${value.toLocaleString('ru-RU', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} ₽`;
}

function fmtPercent(value) {
  return `${value.toLocaleString('ru-RU', { minimumFractionDigits: 1, maximumFractionDigits: 1 })}%`;
}

function periodText(meeting) {
  return meeting.period ? PERIOD_LABELS[meeting.period] : '—';
}

function amountText(meeting) {
  return meeting.dps == null ? '—' : fmtMoney(meeting.dps);
}

function yieldText(meeting) {
  return meeting.divYield == null ? '—' : fmtPercent(meeting.divYield);
}

function logoHtml(ticker) {
  return `
    <span class="company__logo">
      <img src="logos/${ticker}.svg" alt="" width="32" height="32"
           onerror="this.hidden=true;this.nextElementSibling.hidden=false">
      <span class="company__fallback" aria-hidden="true" hidden>${ticker.slice(0, 1)}</span>
    </span>`;
}

function factsHtml(meeting) {
  return `
    <dl class="facts">
      <div><dt>Период</dt><dd>${esc(periodText(meeting))}</dd></div>
      <div><dt>На акцию</dt><dd>${esc(amountText(meeting))}</dd></div>
      <div><dt>Доходность</dt><dd>${esc(yieldText(meeting))}</dd></div>
      <div><dt>Собрание</dt><dd>${fmtDate(meeting.meeting)}</dd></div>
      <div><dt>Отсечка</dt><dd>${fmtDate(meeting.cutoff)}</dd></div>
    </dl>`;
}

function dsiHtml(value, options = {}) {
  const withLabel = options.label !== false;
  const display = value == null ? '—' : String(value);
  return `
    <span class="dsi">
      ${withLabel ? '<span class="dsi__label">DSI</span>' : ''}
      <span class="dsi__value">${display}</span>
      <button type="button" class="dsi__hint" aria-label="${esc(DSI_HINT)}">
        <span aria-hidden="true">i</span>
        <span class="dsi__tooltip" role="tooltip" aria-hidden="true">${esc(DSI_HINT)}</span>
      </button>
    </span>`;
}

function updatedLabel() {
  const minutes = Math.floor((Date.now() - state.refreshedAt) / 60000);
  if (minutes < 1) return 'только что';
  return `${minutes} ${plural(minutes, ['минуту', 'минуты', 'минут'])} назад`;
}

/* ---------- состояние ---------- */

const state = {
  month: DEMO_TODAY.slice(0, 7),
  showPast: false,
  filter: 'all',
  query: '',
  activeOption: -1,
  watchlist: [],
  refreshedAt: Date.now() - 5 * 60000,
  refreshing: false,
  route: { path: '/calendar', meeting: null },
  snackbarTimer: null,
  undo: null
};

let modalOpenId = null;
let triggerEl = null;

/* ---------- хранилище ---------- */

function loadWatchlist() {
  const fallback = DEFAULT_WATCHLIST.slice();
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return fallback;
    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) return fallback;
    return parsed.filter((ticker) => TICKERS.includes(ticker));
  } catch (error) {
    return fallback;
  }
}

function persist() {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(state.watchlist));
  } catch (error) {
    /* хранилище недоступно — прототип продолжает работать в памяти */
  }
}

/* ---------- календарь ---------- */

function cardHtml(meeting) {
  const status = statusOf(meeting);
  const watched = state.watchlist.includes(meeting.ticker);
  const aria = `${meeting.ticker}, ${meeting.issuer}. Выплаты за период: ${periodText(meeting)}. `
    + `На акцию: ${amountText(meeting)}. Доходность: ${yieldText(meeting)}. `
    + `Отсечка ${fmtDate(meeting.cutoff)}. ${status.label}. DSI ${meeting.dsi == null ? 'нет данных' : meeting.dsi}`;
  return `
    <article class="card" role="button" tabindex="0" data-action="open-meeting"
             data-id="${meeting.id}" aria-label="${esc(aria)}">
      <div class="card__head">
        <div class="company">
          ${logoHtml(meeting.ticker)}
          <div class="card__title">
            <span class="ticker">${meeting.ticker}</span>
            <span class="issuer">${esc(meeting.issuer)}</span>
          </div>
        </div>
        ${watched ? `<span class="star" title="В сторожках" aria-label="В сторожках">${icon('star')}</span>` : ''}
      </div>
      ${factsHtml(meeting)}
      <div class="card__foot">
        <span class="chip chip--${status.key}">${esc(status.label)}</span>
        ${dsiHtml(meeting.dsi)}
      </div>
    </article>`;
}

function renderCalendar() {
  const monthMeetings = MEETINGS
    .filter((meeting) => meeting.meeting.startsWith(state.month))
    .sort((a, b) => a.cutoff.localeCompare(b.cutoff));

  const upcoming = monthMeetings.filter((meeting) => daysUntil(meeting.cutoff) >= 0);
  const past = monthMeetings.filter((meeting) => daysUntil(meeting.cutoff) < 0);
  const shownPast = state.showPast ? past : [];

  $('#monthLabel').textContent = monthTitle(state.month);

  if (state.refreshing) {
    $('#calendarMeta').textContent = 'Обновляем данные…';
  } else {
    const total = upcoming.length + shownPast.length;
    const found = total === 0
      ? 'Ничего не найдено'
      : `Найдено: ${total} ${plural(total, ['собрание', 'собрания', 'собраний'])}`;
    $('#calendarMeta').textContent = `${found} · Обновлено ${updatedLabel()}`;
  }

  $('#upcomingGrid').innerHTML = upcoming.map(cardHtml).join('');
  $('#upcomingCount').textContent = upcoming.length
    ? `${upcoming.length} ${plural(upcoming.length, ['собрание', 'собрания', 'собраний'])}`
    : '';

  $('#pastGrid').innerHTML = shownPast.map(cardHtml).join('');
  $('#pastCount').textContent = past.length
    ? `${past.length} ${plural(past.length, ['собрание', 'собрания', 'собраний'])}`
    : '';
  $('#pastSection').hidden = state.refreshing || !(state.showPast && past.length > 0);

  $('#upcomingGrid').hidden = state.refreshing;
  $('#skeletonGrid').hidden = !state.refreshing;

  let emptyTitle = '';
  let emptyText = '';
  if (!state.refreshing) {
    if (monthMeetings.length === 0) {
      emptyTitle = 'В этом месяце собраний нет';
      emptyText = 'Переключите месяц стрелками или включите «Показать прошедшие».';
    } else if (upcoming.length === 0 && past.length > 0 && !state.showPast) {
      emptyTitle = 'Все собрания этого месяца уже прошли';
      emptyText = 'Включите «Показать прошедшие», чтобы увидеть их в списке.';
    }
  }

  $('#calendarEmpty').hidden = !emptyTitle;
  $('#calendarEmptyTitle').textContent = emptyTitle;
  $('#calendarEmptyText').textContent = emptyText;
}

function shiftMonth(delta) {
  const [year, month] = state.month.split('-').map(Number);
  const shifted = new Date(Date.UTC(year, month - 1 + delta, 1));
  state.month = `${shifted.getUTCFullYear()}-${String(shifted.getUTCMonth() + 1).padStart(2, '0')}`;
  renderCalendar();
}

/* ---------- сторожки ---------- */

function nearestMeeting(ticker) {
  const meetings = MEETINGS.filter((meeting) => meeting.ticker === ticker);
  const upcoming = meetings
    .filter((meeting) => daysUntil(meeting.cutoff) >= 0)
    .sort((a, b) => a.cutoff.localeCompare(b.cutoff));
  if (upcoming.length) return upcoming[0];
  return meetings.slice().sort((a, b) => b.cutoff.localeCompare(a.cutoff))[0] || null;
}

function watchItems() {
  return state.watchlist
    .map((ticker) => {
      const meeting = nearestMeeting(ticker);
      return meeting ? { ticker, meeting, status: statusOf(meeting) } : null;
    })
    .filter(Boolean)
    .sort((a, b) => {
      const aPast = a.status.days < 0 ? 1 : 0;
      const bPast = b.status.days < 0 ? 1 : 0;
      return aPast - bPast || a.status.days - b.status.days;
    });
}

function filterItems(items) {
  if (state.filter === 'near') {
    return items.filter((item) => item.status.days >= 0 && item.status.days <= THRESHOLD_DAYS);
  }
  if (state.filter === 'critical') {
    return items.filter((item) => item.status.key === 'critical');
  }
  return items;
}

function watchRowHtml(item) {
  const { ticker, meeting, status } = item;
  return `
    <li class="watch-row">
      <div class="watch-row__head">
        <div class="company">
          ${logoHtml(ticker)}
          <button class="watch-row__main" type="button" data-action="open-meeting" data-id="${meeting.id}">
            <span class="ticker">${ticker}</span>
            <span class="issuer">${esc(meeting.issuer)}</span>
          </button>
        </div>
        <button class="icon-btn icon-btn--sm" type="button" data-action="remove-watch"
                data-ticker="${ticker}" aria-label="Убрать ${ticker} из сторожков" title="Убрать из сторожков">
          ${icon('delete')}
        </button>
      </div>
      ${factsHtml(meeting)}
      <div class="watch-row__foot">
        <span class="chip chip--${status.key}">${shortStatus(status)}</span>
        ${dsiHtml(meeting.dsi)}
      </div>
    </li>`;
}

function renderWatchlist() {
  const all = watchItems();
  const items = filterItems(all);

  $('#watchCount').textContent = all.length
    ? `${all.length} ${plural(all.length, ['тикер', 'тикера', 'тикеров'])}`
    : '';

  $('#watchList').innerHTML = items.map(watchRowHtml).join('');
  $('#watchList').hidden = items.length === 0;

  const empty = $('#watchEmpty');
  empty.hidden = items.length !== 0;

  if (!items.length) {
    if (all.length === 0) {
      $('#watchEmptyTitle').textContent = 'Пока нет сторожков';
      $('#watchEmptyText').textContent = 'Найдите тикер выше и добавьте его — сервис будет следить за датой отсечки.';
      $('#watchEmptyCta').hidden = false;
    } else {
      $('#watchEmptyTitle').textContent = 'Под этот фильтр ничего не подходит';
      $('#watchEmptyText').textContent = 'Снимите фильтр или выберите «Все».';
      $('#watchEmptyCta').hidden = true;
    }
  }
}

function renderBadge() {
  const count = state.watchlist.length;
  $$('.js-badge').forEach((badge) => {
    badge.textContent = String(count);
    badge.hidden = count === 0;
  });
}

function setFilter(filter) {
  state.filter = filter;
  $$('.filter').forEach((button) => {
    button.classList.toggle('is-active', button.dataset.filter === filter);
  });
  renderWatchlist();
}

/* ---------- поиск ---------- */

function searchMatches() {
  const query = state.query.trim().toLowerCase();
  if (!query) return [];
  return TICKERS
    .filter((ticker) => !state.watchlist.includes(ticker))
    .map((ticker) => {
      const meeting = MEETINGS.find((item) => item.ticker === ticker);
      return { ticker, issuer: meeting ? meeting.issuer : '' };
    })
    .filter((item) => item.ticker.toLowerCase().includes(query)
      || item.issuer.toLowerCase().includes(query))
    .slice(0, 6);
}

function hideSearchDropdown() {
  state.activeOption = -1;
  const box = $('#searchResults');
  box.hidden = true;
  const input = $('#tickerSearch');
  input.setAttribute('aria-expanded', 'false');
  input.removeAttribute('aria-activedescendant');
}

function renderSearchResults() {
  const input = $('#tickerSearch');
  const box = $('#searchResults');
  const items = searchMatches();

  $('#searchClear').hidden = state.query.length === 0;

  if (!state.query.trim()) {
    hideSearchDropdown();
    box.innerHTML = '';
    return;
  }

  if (state.activeOption >= items.length) state.activeOption = items.length - 1;

  box.hidden = false;
  input.setAttribute('aria-expanded', 'true');

  if (!items.length) {
    box.innerHTML = '<p class="search__empty">Ничего не найдено или тикер уже в сторожках</p>';
    input.removeAttribute('aria-activedescendant');
    return;
  }

  box.innerHTML = items.map((item, index) => `
    <button type="button" class="search__item ${index === state.activeOption ? 'is-active' : ''}"
            role="option" id="search-opt-${index}" aria-selected="${index === state.activeOption}"
            data-action="add-ticker" data-ticker="${item.ticker}">
      <span class="ticker">${item.ticker}</span>
      <span class="search__issuer">${esc(item.issuer)}</span>
    </button>`).join('');

  if (state.activeOption >= 0) {
    input.setAttribute('aria-activedescendant', `search-opt-${state.activeOption}`);
  } else {
    input.removeAttribute('aria-activedescendant');
  }
}

function clearSearch() {
  state.query = '';
  $('#tickerSearch').value = '';
  $('#searchResults').innerHTML = '';
  hideSearchDropdown();
  $('#searchClear').hidden = true;
  $('#tickerSearch').focus();
}

/* ---------- действия со сторожками ---------- */

function addTicker(ticker, options = {}) {
  if (!ticker || state.watchlist.includes(ticker)) return;
  state.watchlist.push(ticker);
  persist();
  state.query = '';
  $('#tickerSearch').value = '';
  $('#searchResults').innerHTML = '';
  hideSearchDropdown();
  $('#searchClear').hidden = true;
  renderAll();
  if (!options.silent) showSnackbar(`${ticker} добавлен в сторожки`);
  if (options.focusSearch) $('#tickerSearch').focus();
}

function removeTicker(ticker, options = {}) {
  const index = state.watchlist.indexOf(ticker);
  if (index < 0) return;
  state.watchlist.splice(index, 1);
  persist();
  renderAll();
  if (options.silent) {
    state.undo = null;
    return;
  }
  state.undo = { ticker, index };
  showSnackbar(`${ticker} удалён из сторожков`, { label: 'Отменить', action: 'undo-remove' }, 6000);
}

function undoRemove() {
  if (!state.undo) return;
  const { ticker, index } = state.undo;
  if (!state.watchlist.includes(ticker)) {
    state.watchlist.splice(Math.min(index, state.watchlist.length), 0, ticker);
    persist();
    renderAll();
    showSnackbar(`${ticker} восстановлен`);
  }
  state.undo = null;
}

function toggleWatch(ticker) {
  if (state.watchlist.includes(ticker)) {
    removeTicker(ticker, { silent: true });
  } else {
    addTicker(ticker, { silent: true });
  }
}

/* ---------- модалка ---------- */

function currentMeeting() {
  return MEETINGS.find((meeting) => meeting.id === state.route.meeting) || null;
}

function modalHtml(meeting) {
  const status = statusOf(meeting);
  const watched = state.watchlist.includes(meeting.ticker);
  const daysText = status.key === 'past'
    ? 'отсечка прошла'
    : (status.key === 'critical' ? 'сегодня' : daysLabel(status.days));
  return `
    <div class="overlay" data-action="backdrop">
      <div class="modal" role="dialog" aria-modal="true" aria-labelledby="modalTitle">
        <div class="modal__head">
          <div class="modal__identity">
            ${logoHtml(meeting.ticker)}
            <h2 class="modal__title" id="modalTitle">${meeting.ticker} · ${esc(meeting.issuer)}</h2>
          </div>
          <button class="icon-btn modal__close" type="button" data-action="close-modal" aria-label="Закрыть">
            ${icon('close')}
          </button>
        </div>
        <dl class="modal__rows">
          <div><dt>Дата собрания</dt><dd>${fmtDate(meeting.meeting)}</dd></div>
          <div><dt>Дата отсечки (реестр)</dt><dd>${fmtDate(meeting.cutoff)}</dd></div>
          <div><dt>Вопрос о дивидендах</dt><dd>${esc(meeting.agenda)}</dd></div>
          <div><dt>Выплаты за период</dt><dd>${esc(periodText(meeting))}</dd></div>
          <div><dt>Выплата на акцию</dt><dd>${esc(amountText(meeting))}</dd></div>
          <div><dt>Доходность</dt><dd>${esc(yieldText(meeting))}</dd></div>
          <div><dt>До отсечки</dt><dd>${esc(daysText)}</dd></div>
          <div><dt>Статус сторожка</dt><dd id="modalWatchStatus">${statusChipHtml(watched)}</dd></div>
          <div><dt>Источник</dt><dd>
            <a class="link" href="${esc(meeting.source)}" target="_blank" rel="noopener noreferrer">
              раскрытие эмитента ${icon('arrow')}
            </a>
          </dd></div>
          <div><dt>DSI</dt><dd>${dsiHtml(meeting.dsi, { label: false })}</dd></div>
        </dl>
        <div class="modal__actions">
          <button class="btn btn--primary" id="modalWatchBtn" type="button"
                  data-action="toggle-watch" data-ticker="${meeting.ticker}">
            ${watched ? 'Убрать из сторожков' : 'Отслеживать тикер'}
          </button>
          <button class="btn btn--ghost" type="button" data-action="close-modal">Закрыть</button>
        </div>
      </div>
    </div>`;
}

function statusChipHtml(watched) {
  return watched
    ? '<span class="chip chip--normal">в сторожках</span>'
    : '<span class="chip chip--past">не отслеживается</span>';
}

function renderModal() {
  const meeting = currentMeeting();
  const root = $('#modalRoot');

  if (!meeting) {
    if (modalOpenId) {
      root.innerHTML = '';
      document.body.classList.remove('modal-open');
      modalOpenId = null;
    }
    return;
  }

  if (modalOpenId === meeting.id) return;

  hideSnackbar();
  root.innerHTML = modalHtml(meeting);
  modalOpenId = meeting.id;
  document.body.classList.add('modal-open');

  const closeButton = $('.modal__close', root);
  if (closeButton) closeButton.focus();
}

function updateModalWatch() {
  const meeting = currentMeeting();
  if (!meeting) return;
  const watched = state.watchlist.includes(meeting.ticker);
  const statusEl = $('#modalWatchStatus');
  const button = $('#modalWatchBtn');
  if (statusEl) statusEl.innerHTML = statusChipHtml(watched);
  if (button) button.textContent = watched ? 'Убрать из сторожков' : 'Отслеживать тикер';
}

function openMeeting(id) {
  if (state.route.meeting === id) return;
  const meeting = MEETINGS.find((item) => item.id === id);
  if (!meeting) return;
  history.pushState({ meeting: id }, '', `#/calendar?meeting=${encodeURIComponent(id)}`);
  handleRoute();
}

function closeMeeting() {
  if (!state.route.meeting) return;
  if (history.state && history.state.meeting) {
    history.back();
  } else {
    history.replaceState(null, '', '#/calendar');
    handleRoute();
  }
}

function trapFocus(event) {
  const modal = $('.modal');
  if (!modal) return;
  const focusables = $$('a[href], button:not([disabled]), input:not([disabled]), [tabindex]:not([tabindex="-1"])', modal)
    .filter((element) => element.offsetParent !== null);
  if (!focusables.length) return;

  const first = focusables[0];
  const last = focusables[focusables.length - 1];

  if (event.shiftKey && document.activeElement === first) {
    event.preventDefault();
    last.focus();
  } else if (!event.shiftKey && document.activeElement === last) {
    event.preventDefault();
    first.focus();
  }
}

/* ---------- snackbar ---------- */

function showSnackbar(text, action, timeout = 4000) {
  $('#snackbarText').textContent = text;

  const button = $('#snackbarAction');
  if (action) {
    button.hidden = false;
    button.textContent = action.label;
    button.dataset.action = action.action;
  } else {
    button.hidden = true;
    button.textContent = '';
    delete button.dataset.action;
    if (!action) state.undo = null;
  }

  if (!action || action.action !== 'undo-remove') state.undo = null;

  $('#snackbar').classList.add('is-visible');
  window.clearTimeout(state.snackbarTimer);
  state.snackbarTimer = window.setTimeout(hideSnackbar, timeout);
}

function hideSnackbar() {
  $('#snackbar').classList.remove('is-visible');
  state.undo = null;
}

/* ---------- маршрутизация ---------- */

function updateTabs(isWatchlist) {
  $$('[data-nav]').forEach((element) => {
    const active = element.dataset.nav === (isWatchlist ? 'watchlist' : 'calendar');
    if (active) element.setAttribute('aria-current', 'page');
    else element.removeAttribute('aria-current');
  });
}

function handleRoute() {
  const raw = location.hash.replace(/^#/, '') || '/calendar';
  const [pathPart, queryPart] = raw.split('?');
  const path = pathPart || '/calendar';
  const params = new URLSearchParams(queryPart || '');

  if (path !== '/calendar' && path !== '/me') {
    history.replaceState(null, '', '#/calendar');
    handleRoute();
    return;
  }

  const previousMeeting = state.route.meeting;
  const meeting = params.get('meeting');
  state.route = { path, meeting };

  const isWatchlist = path === '/me';
  $('#view-calendar').hidden = isWatchlist;
  $('#view-watchlist').hidden = !isWatchlist;
  document.title = isWatchlist
    ? 'Мои сторожки — Дивидендный календарь'
    : 'Календарь — Дивидендный календарь';

  updateTabs(isWatchlist);
  if (isWatchlist) renderWatchlist();
  else renderCalendar();

  renderModal();

  if (previousMeeting && !meeting && triggerEl) {
    const element = triggerEl;
    triggerEl = null;
    if (element.isConnected && element.offsetParent !== null) element.focus();
  }
}

/* ---------- рендер целиком ---------- */

function renderAll() {
  renderCalendar();
  renderWatchlist();
  renderBadge();
  updateModalWatch();
}

/* ---------- события ---------- */

function onClick(event) {
  if (event.target.closest('.dsi__hint')) return;
  if (!event.target.closest('.search')) hideSearchDropdown();

  const actionEl = event.target.closest('[data-action]');
  if (!actionEl) return;
  const action = actionEl.dataset.action;

  switch (action) {
    case 'prev-month':
      shiftMonth(-1);
      break;
    case 'next-month':
      shiftMonth(1);
      break;
    case 'refresh':
      refreshData();
      break;
    case 'open-meeting': {
      const card = actionEl.closest('.card');
      triggerEl = card || null;
      openMeeting(actionEl.dataset.id);
      break;
    }
    case 'close-modal':
      closeMeeting();
      break;
    case 'backdrop':
      if (event.target === actionEl) closeMeeting();
      break;
    case 'toggle-watch':
      toggleWatch(actionEl.dataset.ticker);
      break;
    case 'remove-watch':
      removeTicker(actionEl.dataset.ticker);
      break;
    case 'undo-remove':
      undoRemove();
      break;
    case 'add-ticker':
      addTicker(actionEl.dataset.ticker, { focusSearch: true });
      break;
    case 'set-filter':
      setFilter(actionEl.dataset.filter);
      break;
    case 'clear-search':
      clearSearch();
      break;
    case 'go-calendar':
      location.hash = '#/calendar';
      break;
    default:
      break;
  }
}

function onKeydown(event) {
  if (event.key === 'Escape') {
    if (state.route.meeting) {
      closeMeeting();
      return;
    }
    if (state.query) {
      clearSearch();
      return;
    }
  }

  if (state.route.meeting && event.key === 'Tab') {
    trapFocus(event);
    return;
  }

  const target = event.target;
  if (!(target instanceof Element)) return;
  if (target.closest('.dsi__hint')) return;
  const roleButton = target.closest('[role="button"][data-action="open-meeting"]');
  if (roleButton && (event.key === 'Enter' || event.key === ' ')) {
    event.preventDefault();
    roleButton.click();
  }
}

function onSearchInput() {
  state.query = $('#tickerSearch').value;
  state.activeOption = -1;
  renderSearchResults();
}

function onSearchKeydown(event) {
  const items = searchMatches();

  if (event.key === 'ArrowDown' && items.length) {
    event.preventDefault();
    state.activeOption = (state.activeOption + 1) % items.length;
    renderSearchResults();
  } else if (event.key === 'ArrowUp' && items.length) {
    event.preventDefault();
    state.activeOption = state.activeOption <= 0 ? items.length - 1 : state.activeOption - 1;
    renderSearchResults();
  } else if (event.key === 'Enter') {
    const pick = items[state.activeOption] || (items.length === 1 ? items[0] : null);
    if (pick) {
      event.preventDefault();
      addTicker(pick.ticker, { focusSearch: true });
    }
  } else if (event.key === 'Escape') {
    event.stopPropagation();
    clearSearch();
  }
}

function refreshData() {
  if (state.refreshing) return;
  state.refreshing = true;
  $('#refreshBtn').disabled = true;
  $('#refreshBtn').classList.add('is-spinning');
  renderCalendar();

  window.setTimeout(() => {
    state.refreshing = false;
    state.refreshedAt = Date.now();
    $('#refreshBtn').disabled = false;
    $('#refreshBtn').classList.remove('is-spinning');
    renderCalendar();
    showSnackbar('Данные обновлены');
  }, 600);
}

function buildSkeleton() {
  $('#skeletonGrid').innerHTML = Array.from({ length: 6 }, () => `
    <div class="card skeleton-card">
      <div class="sk sk--title"></div>
      <div class="sk sk--meta"></div>
      <div class="sk sk--line"></div>
      <div class="sk sk--line short"></div>
      <div class="sk sk--chip"></div>
    </div>`).join('');
}

/* ---------- инициализация ---------- */

function init() {
  state.watchlist = loadWatchlist();
  buildSkeleton();

  if (!location.hash) history.replaceState(null, '', '#/calendar');

  $('#showPast').addEventListener('change', (event) => {
    state.showPast = event.target.checked;
    renderCalendar();
  });

  $('#tickerSearch').addEventListener('input', onSearchInput);
  $('#tickerSearch').addEventListener('keydown', onSearchKeydown);

  document.addEventListener('click', onClick);
  document.addEventListener('keydown', onKeydown);
  window.addEventListener('hashchange', handleRoute);
  window.addEventListener('popstate', handleRoute);

  renderAll();
  handleRoute();
}

init();

