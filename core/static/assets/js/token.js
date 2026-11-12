    function checkPass(form) {
        const p1 = document.getElementById('rp_pass1').value;
        const p2 = document.getElementById('rp_pass2').value;
        const err = document.getElementById('rp_match_err');
        if (p1 !== p2) {
            err.style.display = 'block';
            document.getElementById('rp_pass2').focus();
            return false;
        }
        err.style.display = 'none';
        return true;
    }
    document.getElementById('rp_pass2').addEventListener('input', function() {
        const p1 = document.getElementById('rp_pass1').value;
        const err = document.getElementById('rp_match_err');
        err.style.display = (this.value && this.value !== p1) ? 'block' : 'none';
    });