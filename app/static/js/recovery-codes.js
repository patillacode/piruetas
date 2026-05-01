(function () {
    var checkbox = document.getElementById('saved-confirm');
    var btn = document.getElementById('continue-btn');
    if (checkbox && btn) {
        checkbox.addEventListener('change', function () {
            btn.disabled = !this.checked;
        });
        btn.addEventListener('click', function () {
            if (!btn.disabled) { window.location.href = '/'; }
        });
    }

    var copyBtn = document.getElementById('copy-codes-btn');
    var codesText = document.getElementById('codes-text');

    var downloadLink = document.getElementById('download-codes-link');
    if (downloadLink && codesText) {
        downloadLink.addEventListener('click', function (e) {
            e.preventDefault();
            var blob = new Blob([codesText.textContent], { type: 'text/plain' });
            var url = URL.createObjectURL(blob);
            var a = document.createElement('a');
            a.href = url;
            a.download = 'piruetas-recovery-codes.txt';
            a.click();
            URL.revokeObjectURL(url);
        });
    }

    if (copyBtn && codesText) {
        var strings = window.RECOVERY || {};
        copyBtn.addEventListener('click', function () {
            navigator.clipboard.writeText(codesText.textContent).then(function () {
                copyBtn.textContent = strings.copied || 'Copied!';
                setTimeout(function () { copyBtn.textContent = strings.copyAll || 'Copy all'; }, 2000);
            });
        });
    }
})();
