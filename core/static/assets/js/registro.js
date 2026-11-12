function soloLetras(e) {
    let key   = e.keyCode || e.which;
    let tecla = String.fromCharCode(key).toLowerCase();
    let letras = ' áéíóúabcdefghijklmnñopqrstuvwxyz';
    return letras.indexOf(tecla) !== -1;
}

function soloNumeros(e) {
    let key = e.keyCode || e.which;
    return (key >= 48 && key <= 57);
}

function soloAlfanumerico(e) {
    let key   = e.keyCode || e.which;
    let tecla = String.fromCharCode(key);
    return /^[a-zA-Z0-9]$/.test(tecla);
}

function togglePass(inputId, iconId) {
    const input = document.getElementById(inputId);
    const icon  = document.getElementById(iconId);
    if (input.type === 'password') {
        input.type = 'text';
        icon.classList.replace('fa-eye', 'fa-eye-slash');
    } else {
        input.type = 'password';
        icon.classList.replace('fa-eye-slash', 'fa-eye');
    }
}

function abrirAsistido() {
    document.getElementById('modalAsistido').style.display = 'flex';
}

function cerrarAsistido() {
    document.getElementById('modalAsistido').style.display = 'none';
}

window.onclick = function(event) {
    const modal = document.getElementById('modalAsistido');
    if (event.target === modal) {
        modal.style.display = 'none';
    }
};

const registrationForm = document.getElementById('registerForm');

const fechaNacInput = document.getElementById('fecha_nac');
if (fechaNacInput) {
    const hoy = new Date();
    const hace14Anios = new Date(hoy.getFullYear() - 14, hoy.getMonth(), hoy.getDate());
    fechaNacInput.max = hace14Anios.toISOString().split('T')[0];
}

registrationForm.onsubmit = function(e) {
    const pass    = document.getElementById('password').value;
    const confirm = document.getElementById('confirm_password').value;
    const aceptaTerminos = document.getElementById('aceptaTerminos');

    if (pass !== confirm) {
        e.preventDefault();
        Swal.fire({
            icon: 'warning',
            title: '¡Ups!',
            text: 'Las contraseñas no coinciden.',
            confirmButtonColor: '#0B5AA6'
        });
        return false;
    }

    if (aceptaTerminos && !aceptaTerminos.checked) {
        e.preventDefault();
        Swal.fire({
            icon: 'warning',
            title: 'Términos y Condiciones',
            text: 'Debes leer y aceptar los Términos y Condiciones y la Política de Habeas Data para completar tu registro.',
            confirmButtonColor: '#0B5AA6'
        });
        aceptaTerminos.focus();
        return false;
    }
};