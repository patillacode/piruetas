(function () {
    const I18N = window.ADMIN_I18N;
    const overlay = document.getElementById('user-modal');
    const modal = overlay.querySelector('.modal--user');
    let currentUserId = null;
    let cleanupTrap = null;

    function resetDeleteState() {
        document.getElementById('modal-delete-idle').hidden = false;
        document.getElementById('modal-delete-confirm').hidden = true;
    }

    function openModal(btn) {
        currentUserId = btn.dataset.userId;
        const isAdmin = btn.dataset.isAdmin === 'true';

        document.getElementById('user-modal-title').textContent = btn.dataset.username;
        document.getElementById('modal-entries').textContent =
            btn.dataset.entryCount + ' (' + btn.dataset.pctDays + '%)';
        document.getElementById('modal-last-login').textContent = btn.dataset.lastLogin;
        document.getElementById('modal-storage').textContent = btn.dataset.storage;

        const bannerSection = document.getElementById('modal-banner-section');
        const dangerSection = document.getElementById('modal-danger-section');

        if (isAdmin) {
            bannerSection.hidden = true;
            dangerSection.hidden = true;
        } else {
            bannerSection.hidden = false;
            dangerSection.hidden = false;
            document.getElementById('modal-banner-text').value = btn.dataset.banner;
            document.getElementById('modal-feedback').hidden = true;
            resetDeleteState();
        }

        overlay.hidden = false;
        cleanupTrap = trapFocus(modal);
        document.getElementById('modal-close').focus();
    }

    function closeModal() {
        overlay.hidden = true;
        if (cleanupTrap) { cleanupTrap(); cleanupTrap = null; }
    }

    document.querySelectorAll('.btn-details').forEach(btn => {
        btn.addEventListener('click', () => openModal(btn));
    });

    document.getElementById('modal-close').addEventListener('click', closeModal);
    overlay.addEventListener('click', e => { if (e.target === overlay) closeModal(); });
    document.addEventListener('keydown', e => {
        if (e.key === 'Escape' && !overlay.hidden) closeModal();
    });

    async function postForm(path, fields) {
        const csrf = document.querySelector('meta[name="csrf-token"]').content;
        const body = new URLSearchParams({ csrf_token: csrf, ...fields });
        const res = await fetch(path, {
            method: 'POST',
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
            body: body.toString(),
        });
        return res.ok;
    }

    function showFeedback(msg, ok) {
        const el = document.getElementById('modal-feedback');
        el.textContent = msg;
        el.className = 'modal__feedback ' + (ok ? 'modal__feedback--ok' : 'modal__feedback--error');
        el.hidden = false;
    }

    document.getElementById('modal-set-banner').addEventListener('click', async () => {
        const text = document.getElementById('modal-banner-text').value;
        const ok = await postForm('/admin/users/' + currentUserId + '/set-banner', {
            banner_message: text,
        });
        showFeedback(ok ? I18N.banner_saved : I18N.action_error, ok);
    });

    document.getElementById('modal-clear-banner').addEventListener('click', async () => {
        const ok = await postForm('/admin/users/' + currentUserId + '/clear-banner');
        if (ok) document.getElementById('modal-banner-text').value = '';
        showFeedback(ok ? I18N.banner_cleared : I18N.action_error, ok);
    });

    document.getElementById('modal-delete-btn').addEventListener('click', () => {
        const username = document.getElementById('user-modal-title').textContent;
        document.getElementById('modal-delete-warning').textContent =
            I18N.delete_confirm.replace('{name}', username);
        document.getElementById('modal-delete-form').action =
            '/admin/users/' + currentUserId + '/delete';
        document.getElementById('modal-delete-idle').hidden = true;
        document.getElementById('modal-delete-confirm').hidden = false;
    });

    document.getElementById('modal-delete-cancel').addEventListener('click', resetDeleteState);
})();
