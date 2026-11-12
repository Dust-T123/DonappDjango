from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import PasswordResetConfirmView, PasswordResetView
from django.contrib.messages.views import SuccessMessageMixin
from django.db import IntegrityError, transaction
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.views.decorators.http import require_POST

from ..forms import DonappPasswordResetForm, RegistroForm
from ..models import Usuario
from ..utils import ruta_por_rol

BACKEND = 'django.contrib.auth.backends.ModelBackend'


# ── LOGIN / LOGOUT ───────────────────────────────────────────────────────────

def login_view(request):
    if request.user.is_authenticated:
        return redirect(ruta_por_rol(request.user))

    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        contrasena = request.POST.get('contrasena', '')

        if not email or not contrasena:
            messages.error(request, 'El correo y la contraseña son obligatorios.')
            return render(request, 'core/login.html')

        usuario = Usuario.objects.filter(email__iexact=email).first()

        if usuario is None:
            messages.error(request, 'No encontramos una cuenta con ese correo electrónico.')
        elif not usuario.is_active:
            messages.error(request, 'Tu acceso ha sido restringido por el administrador.')
        elif not usuario.check_password(contrasena):
            messages.error(request, 'Contraseña incorrecta. Verifica tus credenciales.')
        else:
            login(request, usuario, backend=BACKEND)
            return redirect('login_exitoso')

    return render(request, 'core/login.html')


@login_required
def login_exitoso(request):
    """Pantalla de bienvenida (SweetAlert) que redirige al panel del rol.
    Se llega por redirect para que recargar la página no reenvíe el formulario."""
    return render(request, 'core/login_success.html', {
        'nombre': request.user.nombre,
        'ruta': ruta_por_rol(request.user),
    })


@require_POST
def logout_view(request):
    logout(request)
    messages.success(request, 'Sesión cerrada correctamente.')
    return redirect('login')


# ── REGISTRO ─────────────────────────────────────────────────────────────────

def registro_view(request):
    if request.user.is_authenticated:
        return redirect(ruta_por_rol(request.user))

    if request.method == 'POST':
        form = RegistroForm(request.POST)
        if form.is_valid():
            d = form.cleaned_data
            try:
                with transaction.atomic():
                    Usuario.objects.create_user(
                        email=d['email'],
                        password=d['password'],
                        nombre=d['nombre'],
                        apellido=d['apellido'],
                        tipo_documento=d['tipoDocumento'],
                        num_documento=d['numDocumento'],
                        fecha_nacimiento=d['fechaNacimiento'],
                        direccion=d['direccion'],
                        telefono=d['telefono'],
                        necesidad=d['necesidad'] or None,
                        rol='donante',
                        estado='activo',
                    )
            except IntegrityError:
                # Otro registro con el mismo correo/documento llegó justo antes.
                messages.error(request, 'El correo o el número de documento ya están registrados.')
            else:
                messages.success(request, '¡Registro exitoso! Ya puedes iniciar sesión.')
                return redirect('login')
        else:
            # Igual que en Laravel: se muestra el primer error.
            primer_error = next(iter(form.errors.values()))[0]
            messages.error(request, primer_error)

    return render(request, 'core/registro.html')


# ── RECUPERACIÓN DE CONTRASEÑA ───────────────────────────────────────────────

class DonappRecuperarView(SuccessMessageMixin, PasswordResetView):
    template_name = 'core/recuperar.html'
    form_class = DonappPasswordResetForm
    email_template_name = 'core/emails/recuperacion_contrasena.txt'
    html_email_template_name = 'core/emails/recuperacion_contrasena.html'
    subject_template_name = 'core/emails/recuperacion_asunto.txt'
    success_url = reverse_lazy('recuperar')
    # Siempre la misma respuesta (anti-enumeración de cuentas).
    success_message = 'Si el correo pertenece a una cuenta activa, recibirás las instrucciones.'


class DonappRestablecerView(SuccessMessageMixin, PasswordResetConfirmView):
    template_name = 'core/restablecer.html'
    success_url = reverse_lazy('login')
    success_message = 'Contraseña restablecida. Ya puedes iniciar sesión.'
    post_reset_login = False
