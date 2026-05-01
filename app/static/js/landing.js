(function () {
  const { copyLabel, copiedLabel, themeLight, themeDark, heroSub, accentWord } = window.LANDING;

  // ── Hero: animated letters via DOM (no innerHTML on user data) ─────────────
  (function () {
    const el = document.getElementById('hero-headline');
    'Piruetas'.split('').forEach(function (ch, i) {
      var span = document.createElement('span');
      span.className = 'l';
      span.style.animationDelay = (0.3 + i * 0.08) + 's';
      span.textContent = ch;
      el.appendChild(span);
    });

    var subEl = document.getElementById('hero-sub');
    var accentIdx = heroSub.lastIndexOf(accentWord);
    if (accentIdx !== -1) {
      subEl.appendChild(document.createTextNode(heroSub.slice(0, accentIdx)));
      var em = document.createElement('em');
      em.className = 'accent';
      em.textContent = accentWord;
      subEl.appendChild(em);
      subEl.appendChild(document.createTextNode(heroSub.slice(accentIdx + accentWord.length)));
    } else {
      subEl.textContent = heroSub;
    }
  })();

  // ── Theme toggle ───────────────────────────────────────────────────────────
  window.PiruetasTheme.init(function (theme) {
    var lbl = document.getElementById('theme-label');
    if (lbl) lbl.textContent = theme === 'dark' ? themeDark : themeLight;
  });

  // ── Copy buttons ───────────────────────────────────────────────────────────
  document.querySelectorAll('.copy-btn[data-target]').forEach(function (btn) {
    btn.addEventListener('click', function () {
      var target = document.getElementById(btn.getAttribute('data-target'));
      if (!target) return;
      var text = target.tagName === 'PRE' ? target.textContent : target.textContent.trim();
      if (navigator.clipboard) navigator.clipboard.writeText(text);
      btn.textContent = copiedLabel;
      setTimeout(function () { btn.textContent = copyLabel; }, 1200);
    });
  });

  // ── Locale select ─────────────────────────────────────────────────────────
  var langSel = document.getElementById('lang-select');
  if (langSel) {
    langSel.addEventListener('change', function () {
      window.location.href = '/locale/' + langSel.value;
    });
  }

  // ── Scroll reveal ──────────────────────────────────────────────────────────
  var io = new IntersectionObserver(function (entries) {
    entries.forEach(function (e) {
      if (e.isIntersecting) { e.target.classList.add('in'); io.unobserve(e.target); }
    });
  }, { threshold: 0.12 });
  document.querySelectorAll('.reveal').forEach(function (el) { io.observe(el); });
})();
