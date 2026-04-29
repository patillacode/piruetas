(function () {
    var checkbox = document.getElementById('saved-confirm');
    var btn = document.getElementById('continue-btn');
    if (checkbox && btn) {
        checkbox.addEventListener('change', function () {
            if (this.checked) {
                btn.href = '/';
                btn.style.opacity = '1';
                btn.removeAttribute('aria-disabled');
            } else {
                btn.removeAttribute('href');
                btn.style.opacity = '0.4';
                btn.setAttribute('aria-disabled', 'true');
            }
        });
    }

    var copyBtn = document.getElementById('copy-codes-btn');
    var codesText = document.getElementById('codes-text');
    if (copyBtn && codesText) {
        copyBtn.addEventListener('click', function () {
            navigator.clipboard.writeText(codesText.textContent).then(function () {
                copyBtn.textContent = 'Copied!';
                setTimeout(function () { copyBtn.textContent = 'Copy all'; }, 2000);
            });
        });
    }
})();
