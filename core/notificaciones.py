"""Correos transaccionales del personal (equivalentes a los Mailable de Laravel)."""

import logging

from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string

logger = logging.getLogger(__name__)


def _enviar(destino, asunto, plantilla, contexto):
    mensaje = EmailMultiAlternatives(asunto, render_to_string(f'core/emails/{plantilla}.txt', contexto), to=[destino])
    mensaje.attach_alternative(render_to_string(f'core/emails/{plantilla}.html', contexto), 'text/html')
    mensaje.send()


def notificar_estado(usuario, tipo, nuevo_estado, observacion=''):
    """Avisa al usuario el cambio de estado de su donación, solicitud o visita.

    Igual que en Laravel, un fallo de correo NO debe impedir el cambio de estado:
    se registra en el log y se continúa. Devuelve True si se envió.
    """
    try:
        _enviar(usuario.email, f'Donapp – Actualización de tu {tipo}', 'notificacion_estado',
                {'nombre': usuario.nombre, 'tipo': tipo, 'estado': nuevo_estado, 'observacion': observacion})
        return True
    except Exception:
        logger.exception('No se pudo enviar la notificación de estado a %s', usuario.email)
        return False


def enviar_codigo_password(usuario, codigo):
    """Envía el código de 6 dígitos. Aquí SÍ se propaga el error: el usuario debe saber si no llegó."""
    _enviar(usuario.email, 'Donapp – Código para cambiar tu contraseña', 'codigo_cambio_password',
            {'nombre': usuario.nombre, 'codigo': codigo})
