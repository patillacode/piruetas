(function () {
  const themeToggle = document.getElementById('theme-toggle');

  function applyTheme(theme) {
    if (theme === 'dark') {
      document.documentElement.setAttribute('data-theme', 'dark');
      themeToggle.textContent = '\u263d';
    } else {
      document.documentElement.removeAttribute('data-theme');
      themeToggle.textContent = '\u2600';
    }
  }

  const savedTheme = localStorage.getItem('theme') || '';
  applyTheme(savedTheme);

  themeToggle.addEventListener('click', () => {
    const current = document.documentElement.getAttribute('data-theme');
    const next = current === 'dark' ? '' : 'dark';
    localStorage.setItem('theme', next);
    applyTheme(next);
  });

  const localePicker = document.getElementById('language-picker-select');
  if (localePicker) {
    localePicker.addEventListener('change', () => {
      window.location.href = '/locale/' + localePicker.value;
    });
  }
})();
