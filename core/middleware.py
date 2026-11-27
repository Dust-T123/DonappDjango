"""Endurecimiento de sesiones.

- Cierra la sesión tras un rato de inactividad (SESION_INACTIVIDAD_SEG, 30 min por defecto).
- Marca como "no almacenables" las páginas de quien tiene sesión: al cerrar sesión y pulsar
  «Atrás», el navegador ya no muestra el panel guardado en caché.
"""
import time

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import logout
from django.shortcuts import redirect

# Se escribe la marca de actividad como mucho cada tantos segundos (evita una escritura por petición).
_REFRESCO_SEG = 30


class SesionSeguraMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        usuario = getattr(request, 'user', None)
        autenticado = bool(usuario is not None and usuario.is_authenticated)
        if autenticado:
            ahora = time.time()
            ultima = request.session.get('ultima_actividad')
            limite = getattr(settings, 'SESION_INACTIVIDAD_SEG', 1800)
            if ultima is not None and ahora - ultima > limite:
                logout(request)
                messages.info(request, 'Tu sesión se cerró por inactividad. Inicia sesión de nuevo para continuar.')
                return redirect('login')
            if ultima is None or ahora - ultima > _REFRESCO_SEG:
                request.session['ultima_actividad'] = ahora
        respuesta = self.get_response(request)
        if autenticado:
            respuesta['Cache-Control'] = 'no-store, no-cache, must-revalidate, private'
            respuesta['Pragma'] = 'no-cache'
        return respuesta
