from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import PasswordResetConfirmView, PasswordResetView
from django.contrib.messages.views import SuccessMessageMixin
from django.db import IntegrityError, transaction
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.views.decorators.http import require_POST

from django.core.cache import cache

from ..forms import DonappPasswordResetForm, DonappSetPasswordForm, RegistroForm
from ..models import Usuario
from ..utils import PANEL_POR_ROL, ruta_por_rol
from passlib.context import CryptContext

BACKEND = 'django.contrib.auth.backends.ModelBackend'
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Límite de intentos fallidos de inicio de sesión (por correo y por IP).
MAX_INTENTOS_LOGIN = 5          # por correo
MAX_INTENTOS_IP = 30            # por IP (más alto: varias personas pueden compartir red)
VENTANA_BLOQUEO_SEG = 15 * 60


def _claves_intentos(request, email):
    ip = request.META.get('REMOTE_ADDR', '')
    return (f'login_fallos:mail:{email.lower()}', f'login_fallos:ip:{ip}')


def _bloqueado(request, email):
    clave_mail, clave_ip = _claves_intentos(request, email)
    return cache.get(clave_mail, 0) >= MAX_INTENTOS_LOGIN or cache.get(clave_ip, 0) >= MAX_INTENTOS_IP


def _registrar_fallo(request, email):
    for k in _claves_intentos(request, email):
        cache.set(k, cache.get(k, 0) + 1, VENTANA_BLOQUEO_SEG)


def _limpiar_fallos(request, email):
    cache.delete(_claves_intentos(request, email)[0])


# ── LOGIN VIEW ───────────────────────────────────────────────────────────────

def login_view(request):
    if request.user.is_authenticated:
        return redirect(ruta_por_rol(request.user))

    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        contrasena = request.POST.get('contrasena', '')

        if not email or not contrasena:
            messages.error(request, 'El correo y la contraseña son obligatorios.')
            return render(request, 'core/login.html')

        if _bloqueado(request, email):
            messages.error(request, 'Demasiados intentos fallidos. Espera unos minutos antes de volver a intentarlo.')
            return render(request, 'core/login.html')

        usuario = Usuario.objects.filter(email__iexact=email).first()

        if usuario is None:
            _registrar_fallo(request, email)
            messages.error(request, 'No encontramos una cuenta con ese correo electrónico.')
        elif not usuario.is_active:
            messages.error(request, 'Tu acceso ha sido restringido por el administrador.')
        elif usuario.rol not in PANEL_POR_ROL:
            messages.error(request, 'Tu cuenta tiene un rol no válido. Comunícate con el administrador.')
        elif not usuario.check_password(contrasena):
            _registrar_fallo(request, email)
            messages.error(request, 'Contraseña incorrecta. Verifica tus credenciales.')
        else:
            # Compatibilidad con hashes de Laravel ($2y$/$2a$), Django (pbkdf2/bcrypt) y texto plano
            hash_db = getattr(usuario, 'contrasena', usuario.password)
            es_valida = False

            try:
                if hash_db.startswith('$2y$') or hash_db.startswith('$2a$'):
                    es_valida = pwd_context.verify(contrasena, hash_db)
                elif hash_db.startswith('pbkdf2_') or hash_db.startswith('bcrypt'):
                    es_valida = usuario.check_password(contrasena)
                else:
                    es_valida = (contrasena == hash_db)
            except Exception:
                es_valida = usuario.check_password(contrasena)

            if not es_valida:
                _registrar_fallo(request, email)
                messages.error(request, 'Contraseña incorrecta. Verifica tus credenciales.')
            else:
                _limpiar_fallos(request, email)
                login(request, usuario, backend=BACKEND)
                # Redirección directa según el rol del usuario autenticado
                return redirect(ruta_por_rol(usuario))

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
    form_class = DonappSetPasswordForm
    success_url = reverse_lazy('login')
    success_message = 'Contraseña restablecida. Ya puedes iniciar sesión.'
    post_reset_login = False
