(function () {
  const NAMES = {
    en: {
      daysSun: ['Su', 'Mo', 'Tu', 'We', 'Th', 'Fr', 'Sa'],
      daysMon: ['Mo', 'Tu', 'We', 'Th', 'Fr', 'Sa', 'Su'],
      months: ['January','February','March','April','May','June',
               'July','August','September','October','November','December'],
    },
    es: {
      daysSun: ['Do', 'Lu', 'Ma', 'Mi', 'Ju', 'Vi', 'Sa'],
      daysMon: ['Lu', 'Ma', 'Mi', 'Ju', 'Vi', 'Sa', 'Do'],
      months: ['Enero','Febrero','Marzo','Abril','Mayo','Junio',
               'Julio','Agosto','Septiembre','Octubre','Noviembre','Diciembre'],
    },
  };

  const cfg = window.PIRUETAS || {};
  const locale = (cfg.locale && NAMES[cfg.locale]) ? cfg.locale : 'en';
  const names = NAMES[locale];

  // weekStart: 0 = Sunday, 1 = Monday
  const weekStart = cfg.weekStart !== undefined ? cfg.weekStart : 1;
  const DAY_NAMES = weekStart === 1 ? names.daysMon : names.daysSun;
  const MONTH_NAMES = names.months;

  let activeDate = null;
  let displayYear = null;
  let displayMonth = null; // 1-based
  let daysWithEntries = new Set();
  let daysWithShares = new Set();

  async function fetchEntryDays(year, month) {
    try {
      const res = await fetch(`/calendar/${year}/${month}`);
      const data = await res.json();
      daysWithEntries = new Set(data.days);
      daysWithShares = new Set(data.shared || []);
    } catch (e) {
      daysWithEntries = new Set();
      daysWithShares = new Set();
    }
  }

  function render(target) {
    const container = target || document.getElementById('calendar');
    if (!container) return;

    const today = new Date();
    const firstDay = new Date(displayYear, displayMonth - 1, 1);
    const daysInMonth = new Date(displayYear, displayMonth, 0).getDate();
    // Shift getDay() (0=Sun) so column 0 = weekStart
    const startDow = (firstDay.getDay() - weekStart + 7) % 7;

    // Build header
    const header = document.createElement('div');
    header.className = 'calendar__header';

    const prevBtn = document.createElement('button');
    prevBtn.className = 'calendar__nav';
    prevBtn.id = 'cal-prev';
    prevBtn.textContent = '\u2039';
    prevBtn.addEventListener('click', () => navigate(-1));

    const title = document.createElement('span');
    title.className = 'calendar__title';
    title.textContent = `${MONTH_NAMES[displayMonth - 1]} ${displayYear}`;

    const nextBtn = document.createElement('button');
    nextBtn.className = 'calendar__nav';
    nextBtn.id = 'cal-next';
    nextBtn.textContent = '\u203a';
    nextBtn.addEventListener('click', () => navigate(1));

    header.appendChild(prevBtn);
    header.appendChild(title);
    header.appendChild(nextBtn);

    // Build grid
    const grid = document.createElement('div');
    grid.className = 'calendar__grid';

    // Day name headers
    DAY_NAMES.forEach(d => {
      const span = document.createElement('span');
      span.className = 'calendar__day-name';
      span.textContent = d;
      grid.appendChild(span);
    });

    // Empty cells before first day
    for (let i = 0; i < startDow; i++) {
      const span = document.createElement('span');
      span.className = 'calendar__day is-empty';
      grid.appendChild(span);
    }

    // Day cells
    for (let day = 1; day <= daysInMonth; day++) {
      const isToday = (today.getFullYear() === displayYear &&
                       today.getMonth() + 1 === displayMonth &&
                       today.getDate() === day);
      const isActive = (activeDate &&
                        activeDate.year === displayYear &&
                        activeDate.month === displayMonth &&
                        activeDate.day === day);
      const hasEntry = daysWithEntries.has(day);
      const isShared = daysWithShares.has(day);

      const mm = String(displayMonth).padStart(2, '0');
      const dd = String(day).padStart(2, '0');
      const dateStr = `${displayYear}/${mm}/${dd}`;

      let classes = 'calendar__day';
      if (isToday) classes += ' is-today';
      if (isActive) classes += ' is-active';
      if (hasEntry && !isActive) classes += ' has-entry';
      if (isShared && !isActive) classes += ' is-shared';

      const a = document.createElement('a');
      a.className = classes;
      a.href = `/journal/${dateStr}`;
      a.textContent = day;
      grid.appendChild(a);
    }

    container.textContent = '';
    container.appendChild(header);
    container.appendChild(grid);

    if (container.id === 'calendar') {
      const footer = document.createElement('div');
      footer.className = 'calendar__footer';
      const legendBtn = document.createElement('button');
      legendBtn.className = 'calendar__legend-btn';
      legendBtn.textContent = '?';
      legendBtn.setAttribute('aria-label', 'Show calendar legend');
      legendBtn.addEventListener('click', () => {
        const legend = document.getElementById('calendar-legend');
        if (legend) legend.hidden = !legend.hidden;
      });
      footer.appendChild(legendBtn);
      container.appendChild(footer);
    }
  }

  function renderAll() {
    render(document.getElementById('calendar'));
    const mob = document.getElementById('mobile-calendar');
    if (mob) render(mob);
  }

  function navigate(delta) {
    displayMonth += delta;
    if (displayMonth < 1) { displayMonth = 12; displayYear--; }
    if (displayMonth > 12) { displayMonth = 1; displayYear++; }
    fetchEntryDays(displayYear, displayMonth).then(renderAll);
  }

  async function fetchStats() {
    try {
      const res = await fetch('/journal/stats');
      const data = await res.json();
      const el = document.getElementById('sidebar-stats');
      if (!el) return;
      const s = window.PIRUETAS?.strings || {};
      const streakText = data.streak > 0
        ? (s.streakLabel || '{n}-day streak').replace('{n}', data.streak)
        : (s.noStreak || 'No streak yet');
      const entryWord = data.month_entries === 1 ? (s.entrySingular || 'entry') : (s.entryPlural || 'entries');
      const monthText = `${data.month_entries} ${entryWord} \u00b7 ${data.month_words.toLocaleString()} ${s.wordsThisMonth || 'words this month'}`;
      el.textContent = '';
      const streakEl = document.createElement('div');
      streakEl.className = 'sidebar-stats__streak';
      streakEl.textContent = streakText;
      const monthEl = document.createElement('div');
      monthEl.className = 'sidebar-stats__month';
      monthEl.textContent = monthText;
      el.appendChild(streakEl);
      el.appendChild(monthEl);
    } catch {
      // stats are non-critical
    }
  }

  async function init() {
    if (!cfg || !cfg.entryDate) return;

    const [y, m, d] = cfg.entryDate.split('-').map(Number);
    activeDate = { year: y, month: m, day: d };
    displayYear = y;
    displayMonth = m;

    await fetchEntryDays(displayYear, displayMonth);
    renderAll();
    fetchStats();

    const mobileBtn = document.getElementById('mobile-date-btn');
    if (mobileBtn) {
      const months = cfg.months || ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
      mobileBtn.textContent = `${months[m-1]} ${d}, ${y}`;
    }

    const overlay = document.getElementById('mobile-cal-overlay');
    if (mobileBtn && overlay) {
      mobileBtn.addEventListener('click', () => { overlay.hidden = false; });
      overlay.addEventListener('click', (e) => {
        if (e.target === overlay) overlay.hidden = true;
      });
    }

    function offsetDate(year, month, day, delta) {
      const dt = new Date(year, month - 1, day + delta);
      return { year: dt.getFullYear(), month: dt.getMonth() + 1, day: dt.getDate() };
    }
    function dateUrl(year, month, day) {
      return `/journal/${year}/${String(month).padStart(2,'0')}/${String(day).padStart(2,'0')}`;
    }
    const prev = document.getElementById('mobile-prev');
    const next = document.getElementById('mobile-next');
    if (prev) { const p = offsetDate(y, m, d, -1); prev.href = dateUrl(p.year, p.month, p.day); }
    if (next) { const n = offsetDate(y, m, d, 1); next.href = dateUrl(n.year, n.month, n.day); }
  }

  window.calendarRemoveEntry = function(day) {
    daysWithEntries.delete(day);
    daysWithShares.delete(day);
    renderAll();
  };

  document.addEventListener('DOMContentLoaded', init);
})();
