(function () {
  function onThemeApply(theme) {
    const sheetLabel = document.getElementById('sheet-theme-label');
    if (sheetLabel) sheetLabel.textContent = theme === 'dark' ? 'Light mode' : 'Dark mode';
  }

  window.PiruetasTheme.init(onThemeApply);

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
      window.PiruetasTheme.toggle(onThemeApply);
      closeSheet();
    });
  }
})();
