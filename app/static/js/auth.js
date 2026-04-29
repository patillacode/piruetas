(function () {
    var pw = document.getElementById('password') || document.getElementById('new_password');
    var cpw = document.getElementById('confirm_password');
    if (!pw || !cpw) return;
    function check() {
        cpw.setCustomValidity(cpw.value && pw.value !== cpw.value ? 'Passwords do not match' : '');
    }
    pw.addEventListener('input', check);
    cpw.addEventListener('input', check);
})();
