import logging
from functools import wraps

from django.contrib import messages
from django.contrib.auth import logout
from django.shortcuts import redirect, render

from .utils import PANEL_POR_ROL, ruta_por_rol

logger = logging.getLogger('donapp.seguridad')

ETIQUETA_ROL = {'administrador': 'administrador', 'asistente': 'asistente', 'donante': 'donante / solicitante'}


def rol_requerido(*roles):
    """Equivalente al middleware CheckRole de Laravel.

    - Sin sesión: manda al login.
    - Con sesión pero rol equivocado: respuesta 403 con una pantalla de «acceso restringido»
      (no se muestra nada del módulo ajeno) y queda registrado el intento.
    - Con un rol inexistente: cierra la sesión y avisa (no hay panel al que mandarlo).
    La cuenta inactiva y el cambio de contraseña ya los maneja Django: cierra la
    sesión en la siguiente petición (is_active=False o hash de sesión distinto).
    """
    def decorador(vista):
        @wraps(vista)
        def envoltura(request, *args, **kwargs):
            if not request.user.is_authenticated:
                messages.error(request, 'Debes iniciar sesión.')
                return redirect('login')
            if request.user.rol not in PANEL_POR_ROL:
                # Rol que no existe (p. ej. 'Donante' con mayúscula, cargado a mano en la BD). Sin esto el
                # usuario rebotaba entre su "panel" y el decorador en un bucle infinito de redirecciones.
                logout(request)
                messages.error(request, 'Tu cuenta tiene un rol no válido. Comunícate con el administrador.')
                return redirect('login')
            if request.user.rol not in roles:
                logger.warning('Acceso denegado: usuario=%s rol=%s ruta=%s', request.user.pk, request.user.rol, request.path)
                return render(request, 'core/acceso_denegado.html', {
                    'rol_actual': ETIQUETA_ROL.get(request.user.rol, request.user.rol),
                    'roles_permitidos': ' o '.join(ETIQUETA_ROL.get(r, r) for r in roles),
                    'panel_url': ruta_por_rol(request.user),
                }, status=403)
            return vista(request, *args, **kwargs)
        return envoltura
    return decorador
