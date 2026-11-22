"""Panel del administrador (equivalente a AdminController de Laravel).

Donaciones, solicitudes, stock, eventos, visitas, categorías (crear/editar) y perfil propio
son compartidos con el asistente y viven en `gestion.py`. Aquí queda lo exclusivo del
administrador: usuarios y roles, aprobación de correcciones de datos y eliminaciones.

Mejoras de seguridad respecto al original:
  * Aprobar una corrección es una transacción con bloqueo de fila: dos clics (o dos
    administradores) no pueden aplicarla dos veces.
  * El soporte (documento de identidad) se sirve con el tipo real detectado por su
    contenido —no el que declaró quien lo subió—, con `nosniff` y sin caché.
  * No se puede cambiar la propia contraseña desde la edición de usuarios: obliga a pasar
    por el flujo con código al correo.
  * Una categoría con donaciones o solicitudes no se puede eliminar (en Laravel solo se
    ocultaba el botón y la ruta aceptaba el DELETE igual).
"""

import json
import logging

from django.contrib import messages
from django.db import transaction
from django.db.models import Count, Q
from django.http import FileResponse, Http404, HttpResponseForbidden
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from ..decorators import rol_requerido
from ..forms import (
    RechazoCorreccionForm, UsuarioAdminCrearForm, UsuarioAdminEditarForm, validar_numero_documento,
    validar_valor_correccion,
)
from ..models import Categoria, CorreccionDatos, Evento, Usuario
from ..notificaciones import notificar_correccion
from ..utils import fecha_hace_anios
from .comun import ATRIBUTO_CORRECCION, a_panel, almacen_privado, primer_error, procesar_correccion
from .gestion import ORDEN_PRIORIDAD, _iso, _rank_prioridad, datos_gestion

logger = logging.getLogger(__name__)

PANEL = 'dashboard_administrador'

# Nombres de URL que usan las plantillas y el JS compartidos con el asistente.
RUTAS = {
    'panel': 'dashboard_administrador', 'categoria_crear': 'adm_categoria_crear',
    'evento_crear': 'adm_evento_crear', 'evento_estado': 'adm_evento_estado',
    'perfil': 'adm_perfil', 'password_enviar': 'adm_password_enviar',
    'password_confirmar': 'adm_password_confirmar', 'perfil_correccion': 'adm_perfil_correccion',
}

# Firmas de archivo permitidas para el soporte -> (tipo MIME real, extensión)
FIRMAS_SOPORTE = ((b'%PDF-', 'application/pdf', 'pdf'), (b'\x89PNG\r\n\x1a\n', 'image/png', 'png'),
                  (b'\xff\xd8\xff', 'image/jpeg', 'jpg'))


# ── DASHBOARD ────────────────────────────────────────────────────────────────

@rol_requerido('administrador')
def dashboard_administrador(request):
    g = request.GET
    yo = request.user

    usuarios = Usuario.objects.all()
    if g.get('search'):
        s = g['search']
        usuarios = usuarios.filter(Q(nombre__icontains=s) | Q(apellido__icontains=s) | Q(email__icontains=s))
    if g.get('rol') in ('administrador', 'asistente', 'donante'):
        usuarios = usuarios.filter(rol=g['rol'])
    if g.get('prioridad') in ORDEN_PRIORIDAD:
        usuarios = usuarios.filter(prioridad=g['prioridad'])
    if g.get('sort') == 'prioridad':
        usuarios = usuarios.annotate(_r=_rank_prioridad('prioridad')).order_by('_r', '-id')
    else:
        usuarios = usuarios.order_by(*{'az': ('nombre', 'id'), 'za': ('-nombre', 'id')}.get(g.get('sort'), ('-id',)))
    usuarios = list(usuarios)
    for u in usuarios:
        u.json = json.dumps({
            'idUsuario': u.id, 'nombre': u.nombre, 'apellido': u.apellido, 'tipoDocumento': u.tipo_documento,
            'numDocumento': u.num_documento, 'fechaNacimiento': _iso(u.fecha_nacimiento),
            'direccion': u.direccion, 'email': u.email, 'telefono': u.telefono, 'necesidad': u.necesidad or '',
            'rol': u.rol, 'estado': u.estado, 'prioridad': u.prioridad or '',
            'observacion_visita': u.observacion_visita or '',
        }, ensure_ascii=False)

    categorias = Categoria.objects.select_related('creado_por').annotate(
        donaciones_count=Count('donaciones', distinct=True), solicitudes_count=Count('solicitudes', distinct=True))
    if g.get('cat_search'):
        categorias = categorias.filter(nombre__icontains=g['cat_search'])
    categorias = list(categorias.order_by('-nombre' if g.get('cat_sort') == 'za' else 'nombre'))
    for c in categorias:
        c.json = json.dumps({'idCategoria': c.id, 'nombre': c.nombre}, ensure_ascii=False)
        c.eliminable = c.donaciones_count == 0 and c.solicitudes_count == 0

    contexto = datos_gestion(request)
    contexto |= {
        'yo': yo, 'usuarios': usuarios, 'categorias': categorias,
        'todas_categorias': list(Categoria.objects.order_by('nombre')),
        'correcciones': CorreccionDatos.objects.filter(estado='pendiente')
                        .select_related('usuario', 'solicitante').order_by('-id'),
        'total_usuarios': Usuario.objects.count(), 'total_categorias': Categoria.objects.count(),
        'categorias_existentes': [{'id': c.id, 'nombre': c.nombre.strip().lower()} for c in categorias] if not
        g.get('cat_search') else [{'id': c.id, 'nombre': c.nombre.strip().lower()}
                                  for c in Categoria.objects.all()],
        'edad_minima_nacimiento': fecha_hace_anios(14, timezone.localdate()),
        'ruta': RUTAS,
    }
    return render(request, 'core/dashboard_administrador.html', contexto)


# ── USUARIOS ─────────────────────────────────────────────────────────────────

@rol_requerido('administrador')
@require_POST
def usuario_crear(request):
    form = UsuarioAdminCrearForm(request.POST)
    if not form.is_valid():
        messages.error(request, primer_error(form))
        return a_panel(PANEL, 'usuarios')
    c = form.cleaned_data
    es_donante = c['rol'] == 'donante'
    Usuario.objects.create_user(
        email=c['email'], password=c['password'], rol=c['rol'], estado=c['estado'],
        nombre=c['nombre'], apellido=c['apellido'], tipo_documento=c['tipoDocumento'],
        num_documento=c['numDocumento'], fecha_nacimiento=c['fechaNacimiento'], direccion=c['direccion'],
        telefono=c['telefono'],
        # necesidad / prioridad / observación solo existen para donantes (regla de la BD)
        necesidad=(c['necesidad'] or None) if es_donante else None,
        prioridad=(c['prioridad'] or None) if es_donante else None,
        observacion_visita=(c['observacion_visita'] or None) if es_donante else None)
    messages.success(request, 'Usuario creado correctamente.')
    return a_panel(PANEL, 'usuarios')


@rol_requerido('administrador')
@require_POST
def usuario_editar(request, pk):
    usuario = get_object_or_404(Usuario, pk=pk)
    form = UsuarioAdminEditarForm(request.POST, usuario=usuario)
    if not form.is_valid():
        messages.error(request, primer_error(form))
        return a_panel(PANEL, 'usuarios')
    c = form.cleaned_data
    if usuario.pk == request.user.pk:
        if c['rol'] != usuario.rol:
            messages.error(request, 'No puedes cambiar tu propio rol.')
            return a_panel(PANEL, 'usuarios')
        if c['estado'] != 'activo':
            messages.error(request, 'No puedes desactivar tu propia cuenta.')
            return a_panel(PANEL, 'usuarios')
        if c['password']:
            messages.error(request, 'Para cambiar tu propia contraseña usa "Mi perfil", que la confirma con un código.')
            return a_panel(PANEL, 'usuarios')
    # nombre / documento / fecha de nacimiento NO se editan aquí: van por solicitud de corrección.
    es_donante = c['rol'] == 'donante'
    usuario.email, usuario.telefono, usuario.direccion = c['email'], c['telefono'], c['direccion']
    usuario.rol, usuario.estado = c['rol'], c['estado']
    usuario.necesidad = (c['necesidad'] or None) if es_donante else None
    usuario.prioridad = (c['prioridad'] or None) if es_donante else None
    usuario.observacion_visita = (c['observacion_visita'] or None) if es_donante else None
    if c['password']:
        usuario.set_password(c['password'])
    usuario.save()
    messages.success(request, 'Usuario actualizado.')
    return a_panel(PANEL, 'usuarios')


@rol_requerido('administrador')
@require_POST
def usuario_toggle_estado(request, pk):
    if pk == request.user.pk:
        messages.error(request, 'No puedes cambiar tu propio estado.')
        return a_panel(PANEL, 'usuarios')
    usuario = get_object_or_404(Usuario, pk=pk)
    usuario.estado = 'inactivo' if usuario.estado == 'activo' else 'activo'
    usuario.save(update_fields=['estado'])
    messages.success(request, f'Usuario {usuario.estado} correctamente.')
    return a_panel(PANEL, 'usuarios')


@rol_requerido('administrador')
@require_POST
def usuario_solicitar_correccion(request, pk):
    return procesar_correccion(
        request, get_object_or_404(Usuario, pk=pk), a_panel(PANEL, 'usuarios'),
        'Solicitud de corrección enviada. Quedará pendiente de aprobación por otro administrador.')


# ── CORRECCIONES DE DATOS (doble control) ────────────────────────────────────

def _validar_valor_correccion(campo, valor, usuario):
    """Devuelve (valor_normalizado, None) o (None, mensaje_de_error).

    El formato lo valida `validar_valor_correccion` (el mismo que se aplica al crear la
    solicitud); aquí se añade solo lo que depende de la base de datos."""
    valor, error = validar_valor_correccion(campo, valor, usuario)
    if error:
        return None, error
    if campo == 'tipoDocumento':
        # El nuevo tipo debe ser coherente con el número que el usuario tiene hoy.
        error = validar_numero_documento(valor, usuario.num_documento)
        if error:
            return None, ('El número actual del documento no es válido para ese tipo. Corrige primero '
                          'el número de documento. ' + error)
    if campo == 'numDocumento' and Usuario.objects.filter(num_documento__iexact=valor) \
            .exclude(pk=usuario.pk).exists():
        return None, 'Ese número de documento ya está registrado por otro usuario.'
    return valor, None


def _purgar_soporte(correccion):
    """Borra el documento de identidad al resolver la solicitud (retención limitada)."""
    if correccion.soporte_ruta:
        try:
            almacen_privado().delete(correccion.soporte_ruta)
        except OSError:
            logger.exception('No se pudo borrar el soporte %s', correccion.soporte_ruta)
        correccion.soporte_ruta = correccion.soporte_mime = None
        correccion.save(update_fields=['soporte_ruta', 'soporte_mime'])


@rol_requerido('administrador')
@require_POST
def correccion_aprobar(request, pk):
    """Aplica el cambio real al usuario. Nunca la aprueba quien la solicitó."""
    with transaction.atomic():
        correccion = get_object_or_404(CorreccionDatos.objects.select_for_update(), pk=pk)
        if correccion.estado != 'pendiente':
            messages.error(request, 'Esta solicitud ya fue resuelta anteriormente.')
            return a_panel(PANEL, 'usuarios')
        if correccion.solicitante_id == request.user.pk:
            messages.error(request, 'No puedes aprobar una solicitud de corrección que tú mismo pediste. '
                                    'Debe hacerlo otro administrador.')
            return a_panel(PANEL, 'usuarios')
        afectado = correccion.usuario
        valor, error = _validar_valor_correccion(correccion.campo, correccion.valor_nuevo.strip(), afectado)
        if error:
            messages.error(request, error)
            return a_panel(PANEL, 'usuarios')
        atributo = ATRIBUTO_CORRECCION[correccion.campo]
        setattr(afectado, atributo, valor)
        afectado.save(update_fields=[atributo])
        correccion.estado, correccion.aprobador = 'aprobada', request.user
        correccion.fecha_resolucion = timezone.now()
        correccion.save(update_fields=['estado', 'aprobador', 'fecha_resolucion'])
    _purgar_soporte(correccion)
    notificar_correccion(afectado, correccion.campo, 'aprobada', valor_nuevo=str(valor))
    messages.success(request, 'Corrección aprobada y aplicada al usuario.')
    return a_panel(PANEL, 'usuarios')


@rol_requerido('administrador')
@require_POST
def correccion_rechazar(request, pk):
    form = RechazoCorreccionForm(request.POST)
    if not form.is_valid():
        messages.error(request, primer_error(form))
        return a_panel(PANEL, 'usuarios')
    motivo = form.cleaned_data['motivo']
    with transaction.atomic():
        correccion = get_object_or_404(CorreccionDatos.objects.select_for_update(), pk=pk)
        if correccion.estado != 'pendiente':
            messages.error(request, 'Esta solicitud ya fue resuelta anteriormente.')
            return a_panel(PANEL, 'usuarios')
        correccion.estado, correccion.aprobador = 'rechazada', request.user
        correccion.fecha_resolucion, correccion.observacion_resolucion = timezone.now(), motivo or None
        correccion.save(update_fields=['estado', 'aprobador', 'fecha_resolucion', 'observacion_resolucion'])
    _purgar_soporte(correccion)
    notificar_correccion(correccion.usuario, correccion.campo, 'rechazada', motivo=motivo)
    messages.success(request, 'Corrección rechazada.')
    return a_panel(PANEL, 'usuarios')


@rol_requerido('administrador')
@require_GET
def correccion_soporte(request, pk):
    """Muestra el documento solo a un administrador distinto de quien pidió la corrección,
    y deja registro de quién lo consultó y cuándo (responsabilidad demostrada, Ley 1581)."""
    correccion = get_object_or_404(CorreccionDatos, pk=pk)
    if correccion.solicitante_id == request.user.pk:
        return HttpResponseForbidden('No puedes ver el soporte de una solicitud que tú mismo hiciste.')
    almacen = almacen_privado()
    if not correccion.soporte_ruta or not almacen.exists(correccion.soporte_ruta):
        raise Http404('El soporte ya no está disponible (fue purgado o la solicitud ya se resolvió).')
    archivo = almacen.open(correccion.soporte_ruta, 'rb')
    cabecera = archivo.read(8)
    archivo.seek(0)
    tipo, extension = next(((t, e) for firma, t, e in FIRMAS_SOPORTE if cabecera.startswith(firma)), (None, None))
    if tipo is None:  # contenido que no es ni PDF ni imagen: no se sirve
        archivo.close()
        raise Http404('El archivo de soporte no es válido.')
    logger.info('Consulta de soporte de corrección: correccion=%s admin=%s fecha=%s',
                correccion.pk, request.user.pk, timezone.now().isoformat())
    respuesta = FileResponse(archivo, content_type=tipo)
    respuesta['Content-Disposition'] = f'inline; filename="soporte-correccion-{pk}.{extension}"'
    respuesta['X-Content-Type-Options'] = 'nosniff'
    respuesta['Cache-Control'] = 'private, no-store'
    return respuesta


# ── ELIMINACIONES ────────────────────────────────────────────────────────────

@rol_requerido('administrador')
@require_POST
def categoria_eliminar(request, pk):
    categoria = get_object_or_404(
        Categoria.objects.annotate(d=Count('donaciones', distinct=True), s=Count('solicitudes', distinct=True)), pk=pk)
    if categoria.d or categoria.s:
        messages.error(request, 'No se puede eliminar una categoría que tiene donaciones o solicitudes asociadas.')
        return a_panel(PANEL, 'categorias')
    categoria.delete()
    messages.success(request, 'Categoría eliminada.')
    return a_panel(PANEL, 'categorias')


@rol_requerido('administrador')
@require_POST
def evento_eliminar(request, pk):
    get_object_or_404(Evento, pk=pk).delete()
    messages.success(request, 'Evento eliminado.')
    return a_panel(PANEL, 'eventos')
