document.querySelectorAll('[data-reset-for]').forEach(btn => {
    btn.addEventListener('click', () => {
        document.getElementById(btn.dataset.resetFor).style.display = 'block';
        btn.style.display = 'none';
    });
});
document.querySelectorAll('form[data-confirm]').forEach(form => {
    form.addEventListener('submit', e => {
        if (!confirm(form.dataset.confirm)) e.preventDefault();
    });
});
