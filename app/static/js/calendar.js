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

  async function init() {
    if (!cfg || !cfg.entryDate) return;

    const [y, m, d] = cfg.entryDate.split('-').map(Number);
    activeDate = { year: y, month: m, day: d };
    displayYear = y;
    displayMonth = m;

    await fetchEntryDays(displayYear, displayMonth);
    renderAll();

    const mobileBtn = document.getElementById('mobile-date-btn');
    const overlay = document.getElementById('mobile-cal-overlay');
    if (mobileBtn && overlay) {
      mobileBtn.addEventListener('click', () => { overlay.hidden = false; });
      overlay.addEventListener('click', (e) => {
        if (e.target === overlay) overlay.hidden = true;
      });
    }
  }

  document.addEventListener('DOMContentLoaded', init);
})();
