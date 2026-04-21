(function () {
  const themeToggle = document.getElementById('theme-toggle');

  function applyTheme(theme) {
    if (theme === 'dark') {
      document.documentElement.setAttribute('data-theme', 'dark');
      if (themeToggle) themeToggle.textContent = '\u263d';
      const sheetLabel = document.getElementById('sheet-theme-label');
      if (sheetLabel) sheetLabel.textContent = 'Light mode';
    } else {
      document.documentElement.removeAttribute('data-theme');
      if (themeToggle) themeToggle.textContent = '\u2600';
      const sheetLabel = document.getElementById('sheet-theme-label');
      if (sheetLabel) sheetLabel.textContent = 'Dark mode';
    }
  }

  const savedTheme = localStorage.getItem('theme') || '';
  applyTheme(savedTheme);

  if (themeToggle) {
    themeToggle.addEventListener('click', () => {
      const current = document.documentElement.getAttribute('data-theme');
      const next = current === 'dark' ? '' : 'dark';
      localStorage.setItem('theme', next);
      applyTheme(next);
    });
  }

  const localePicker = document.getElementById('language-picker-select');
  if (localePicker) {
    localePicker.addEventListener('change', () => {
      window.location.href = '/locale/' + localePicker.value;
    });
  }

  // Mobile bottom sheet
  const overlay = document.getElementById('mobile-sheet-overlay');
  const sheet = document.getElementById('mobile-sheet');
  const menuBtn = document.getElementById('mobile-menu-btn');

  function openSheet() {
    if (!sheet || !overlay) return;
    overlay.removeAttribute('hidden');
    sheet.removeAttribute('hidden');
    requestAnimationFrame(() => {
      overlay.classList.add('open');
      sheet.classList.add('open');
    });
  }

  function closeSheet() {
    if (!sheet || !overlay) return;
    overlay.classList.remove('open');
    sheet.classList.remove('open');
    sheet.addEventListener('transitionend', () => {
      overlay.setAttribute('hidden', '');
      sheet.setAttribute('hidden', '');
    }, { once: true });
  }

  window._closeSheet = closeSheet;

  if (menuBtn) menuBtn.addEventListener('click', openSheet);
  if (overlay) overlay.addEventListener('click', closeSheet);

  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && sheet && !sheet.hidden) closeSheet();
  });

  const sheetThemeBtn = document.getElementById('sheet-theme-toggle');
  if (sheetThemeBtn) {
    sheetThemeBtn.addEventListener('click', () => {
      const current = document.documentElement.getAttribute('data-theme');
      const next = current === 'dark' ? '' : 'dark';
      localStorage.setItem('theme', next);
      applyTheme(next);
      closeSheet();
    });
  }
})();
