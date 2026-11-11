const togglePassword = document.querySelector('#togglePassword');
const password       = document.querySelector('#contrasena');
const eyeIcon        = document.querySelector('#eyeIcon');

togglePassword.addEventListener('click', function () {
    const type = password.getAttribute('type') === 'password' ? 'text' : 'password';
    password.setAttribute('type', type);
    eyeIcon.classList.toggle('fa-eye');
    eyeIcon.classList.toggle('fa-eye-slash');
});
