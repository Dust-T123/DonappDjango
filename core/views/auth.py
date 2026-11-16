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
from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from ..models import (
    Usuario, Categoria, Evento, Donacion, Solicitud, 
    DonacionUsuario, VisitaDomiciliaria, VisitaObservacion, CorreccionDatos
)
BACKEND = 'django.contrib.auth.backends.ModelBackend'


from passlib.context import CryptContext
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def rol_requerido(*roles_permitidos):
    """
    Decorador para restringir el acceso a vistas según el rol del usuario.
    Si no cumple con el rol, lo redirige a su panel asignado.
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                messages.error(request, 'Debes iniciar sesión para acceder.')
                return redirect('login')
            
            if request.user.rol not in roles_permitidos:
                messages.error(request, 'No tienes permisos para acceder a esta sección.')
                return redirect(ruta_por_rol(request.user))
                
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator

# ── AUXILIAR DE REDIRECCIÓN ──────────────────────────────────────────────────

def ruta_por_rol(usuario):
    """
    Retorna el nombre del name en urls.py según el rol del usuario.
    """
    if usuario.rol == 'administrador':
        return 'dashboard_administrador'
    elif usuario.rol == 'asistente':
        return 'dashboard_asistente'
    return 'dashboard_usuario'


@login_required
def dashboard_administrador(request):
    if request.user.rol != 'administrador':
        return redirect(ruta_por_rol(request.user))

    context = {
        'total_usuarios': Usuario.objects.count(),
        'total_donaciones': Donacion.objects.count(),
        'solicitudes_pendientes': Solicitud.objects.filter(estado='pendiente').count(),
        'visitas_pendientes': VisitaDomiciliaria.objects.filter(estado='pendiente').count(),
        'ultimos_usuarios': Usuario.objects.order_by('-id')[:5],
    }
    return render(request, 'core/dashboard_administrador.html', context)


@login_required
def dashboard_asistente(request):
    if request.user.rol not in ('asistente', 'administrador'):
        return redirect(ruta_por_rol(request.user))

    context = {
        'visitas_pendientes': VisitaDomiciliaria.objects.filter(estado='pendiente'),
        'solicitudes_revision': Solicitud.objects.filter(estado='pendiente'),
    }
    return render(request, 'core/dashboard_asistente.html', context)


@login_required
def dashboard_usuario(request):
    # Donante / Usuario regular
    context = {
        'mis_donaciones': DonacionUsuario.objects.filter(donante=request.user),
        'mis_solicitudes': Solicitud.objects.filter(solicitante=request.user),
        'mis_visitas': VisitaDomiciliaria.objects.filter(usuario=request.user),
    }
    return render(request, 'core/dashboard_usuario.html', context)
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

        usuario = Usuario.objects.filter(email__iexact=email).first()

        if usuario is None:
            messages.error(request, 'No encontramos una cuenta con ese correo electrónico.')
        elif not usuario.is_active:
            messages.error(request, 'Tu acceso ha sido restringido por el administrador.')
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
                messages.error(request, 'Contraseña incorrecta. Verifica tus credenciales.')
            else:
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
    success_url = reverse_lazy('login')
    success_message = 'Contraseña restablecida. Ya puedes iniciar sesión.'
    post_reset_login = False
