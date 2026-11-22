"""Utilidades compartidas por los paneles (donante, asistente y, luego, administrador)."""

import hashlib
import uuid
from urllib.parse import urlencode

from django.conf import settings
from django.contrib import messages
from django.core.files.storage import FileSystemStorage
from django.shortcuts import redirect
from django.urls import reverse

from ..forms import CorreccionForm
from ..models import CorreccionDatos

# Campo del formulario de corrección -> atributo del modelo Usuario.
ATRIBUTO_CORRECCION = {
    'nombre': 'nombre', 'apellido': 'apellido', 'tipoDocumento': 'tipo_documento',
    'numDocumento': 'num_documento', 'fechaNacimiento': 'fecha_nacimiento',
}


def almacen_privado():
    """Disco privado: los documentos de identidad NO deben quedar en MEDIA_ROOT (público)."""
    return FileSystemStorage(location=settings.PRIVATE_MEDIA_ROOT)


def primer_error(form):
    """Igual que en Laravel: se muestra solo el primer error de validación."""
    return next(iter(form.errors.values()))[0]


def a_panel(nombre_url, tab, **extra):
    """Redirige al panel conservando la pestaña activa (?tab=...)."""
    return redirect(f"{reverse(nombre_url)}?{urlencode({'tab': tab, **extra})}")


def url_imagen(campo):
    return campo.url if campo else ''


class CorreccionDuplicada(Exception):
    """Ya hay una corrección pendiente de ese usuario para ese campo."""


def crear_correccion(solicitante, usuario, datos):
    """Registra una solicitud de corrección de datos sensibles (habeas data).

    `datos` es el cleaned_data de CorreccionForm. El soporte se guarda en disco
    privado con nombre aleatorio (nunca el que envía el usuario) y con su hash
    SHA-256 para verificar integridad; jamás en la base de datos.
    """
    # En Laravel esto lo frenaba un trigger de MySQL (tg_evitar_correccion_duplicada);
    # en Django se valida aquí, ANTES de guardar el archivo, para no dejar soportes huérfanos.
    if CorreccionDatos.objects.filter(usuario=usuario, campo=datos['campo'], estado='pendiente').exists():
        raise CorreccionDuplicada
    archivo = datos['soporte']
    sha = hashlib.sha256()
    for trozo in archivo.chunks():
        sha.update(trozo)
    extension = archivo.name.rsplit('.', 1)[-1].lower()
    ruta = almacen_privado().save(f'correcciones/{uuid.uuid4().hex}.{extension}', archivo)
    return CorreccionDatos.objects.create(
        usuario=usuario, solicitante=solicitante, campo=datos['campo'],
        valor_anterior=str(getattr(usuario, ATRIBUTO_CORRECCION[datos['campo']])),
        valor_nuevo=datos['valorNuevo'], justificacion=datos['justificacion'], estado='pendiente',
        soporte_ruta=ruta, soporte_mime=archivo.content_type, soporte_hash=sha.hexdigest(),
        consentimiento=True)


def procesar_correccion(request, usuario, volver, mensaje_ok):
    """Flujo completo de "solicitar corrección de datos" (formulario -> registro -> aviso).

    `volver` es la respuesta (redirección) con la que termina la acción en todos los casos.
    """
    form = CorreccionForm(request.POST, request.FILES, usuario=usuario)
    if not form.is_valid():
        messages.error(request, primer_error(form))
        return volver
    try:
        crear_correccion(request.user, usuario, form.cleaned_data)
    except CorreccionDuplicada:
        messages.error(request, 'Ese usuario ya tiene una solicitud pendiente para ese campo. '
                                'Espera su resolución.')
        return volver
    messages.success(request, mensaje_ok)
    return volver
