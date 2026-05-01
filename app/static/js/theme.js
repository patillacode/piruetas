(function () {
  function applyTheme(theme, onApply) {
    if (theme === 'dark') {
      document.documentElement.setAttribute('data-theme', 'dark');
    } else {
      document.documentElement.removeAttribute('data-theme');
    }
    if (onApply) onApply(theme);
  }

  function toggle(onApply) {
    const current = document.documentElement.getAttribute('data-theme');
    const next = current === 'dark' ? '' : 'dark';
    localStorage.setItem('theme', next);
    applyTheme(next, onApply);
    return next;
  }

  const saved = localStorage.getItem('theme') || '';
  // Normalise legacy 'light' value written by older code
  const initial = saved === 'light' ? '' : saved;
  if (initial !== saved) localStorage.setItem('theme', initial);

  window.PiruetasTheme = {
    init: function (onApply) {
      applyTheme(initial, onApply);

      var btn = document.getElementById('theme-toggle');
      if (btn) btn.addEventListener('click', function () { toggle(onApply); });
    },
    toggle: toggle,
  };
})();
