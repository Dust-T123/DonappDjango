"""Panel del asistente (equivalente a AsisController de Laravel).

Lo que comparte con el administrador (donaciones, solicitudes, stock, eventos, visitas,
categorías y perfil) vive en `gestion.py`. Aquí queda lo exclusivo del asistente: la
gestión de donantes/solicitantes.

Diferencias de seguridad respecto al original:
  * Laravel permitía que un asistente editara, desactivara o pidiera correcciones sobre
    CUALQUIER usuario por id (incluidos administradores). Aquí todas las acciones sobre
    usuarios quedan limitadas a usuarios con rol donante.
  * Las acciones que cambian datos son solo POST.
"""

import json

from django.contrib import messages
from django.db.models import Prefetch, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from ..decorators import rol_requerido
from ..forms import DonanteCrearForm, DonanteEditarForm
from ..models import Categoria, CorreccionDatos, Donacion, DonacionUsuario, Solicitud, Usuario
from ..utils import fecha_hace_anios
from .comun import a_panel, primer_error, procesar_correccion
from .gestion import ORDEN_PRIORIDAD, _iso, _rank_prioridad, datos_gestion

PANEL = 'dashboard_asistente'

# Nombres de URL que usan las plantillas y el JS compartidos con el administrador.
RUTAS = {
    'panel': 'dashboard_asistente', 'categoria_crear': 'asis_categoria_crear',
    'evento_crear': 'asis_evento_crear', 'evento_estado': 'asis_evento_estado',
    'perfil': 'asis_perfil', 'password_enviar': 'asis_password_enviar',
    'password_confirmar': 'asis_password_confirmar', 'perfil_correccion': 'asis_perfil_correccion',
}


def _donante_o_404(pk):
    """El asistente solo gestiona donantes/solicitantes, nunca a otro personal."""
    return get_object_or_404(Usuario, pk=pk, rol='donante')


# ── DASHBOARD ────────────────────────────────────────────────────────────────

@rol_requerido('asistente')
def dashboard_asistente(request):
    g = request.GET
    yo = request.user

    # Donantes / solicitantes
    donantes = Usuario.objects.filter(rol='donante')
    if g.get('cli_search'):
        s = g['cli_search']
        donantes = donantes.filter(Q(nombre__icontains=s) | Q(apellido__icontains=s) | Q(email__icontains=s))
    if g.get('cli_prioridad') in ORDEN_PRIORIDAD:
        donantes = donantes.filter(prioridad=g['cli_prioridad'])
    donantes = donantes.order_by(
        {'az': 'nombre', 'za': '-nombre'}.get(g.get('cli_sort'), '-id')
    ) if g.get('cli_sort') != 'prioridad' else donantes.annotate(_r=_rank_prioridad('prioridad')).order_by('_r', '-id')
    donantes = list(donantes)
    for c in donantes:
        c.json = json.dumps({
            'idUsuario': c.id, 'nombre': c.nombre, 'apellido': c.apellido, 'tipoDocumento': c.tipo_documento,
            'numDocumento': c.num_documento, 'fechaNacimiento': _iso(c.fecha_nacimiento), 'email': c.email,
            'telefono': c.telefono, 'direccion': c.direccion, 'necesidad': c.necesidad or '',
            'prioridad': c.prioridad or '', 'observacion_visita': c.observacion_visita or '', 'estado': c.estado,
        }, ensure_ascii=False)
        c.json_hist = json.dumps({'idUsuario': c.id, 'nombre': c.nombre}, ensure_ascii=False)

    # Categorías
    categorias_filtradas = Categoria.objects.all()
    if g.get('cat_search'):
        categorias_filtradas = categorias_filtradas.filter(nombre__icontains=g['cat_search'])
    categorias_filtradas = list(categorias_filtradas.order_by('-nombre' if g.get('cat_sort') == 'za' else 'nombre'))
    for c in categorias_filtradas:
        c.json = json.dumps({'idCategoria': c.id, 'nombre': c.nombre}, ensure_ascii=False)
    todas_categorias = list(Categoria.objects.order_by('nombre'))

    contexto = datos_gestion(request)
    contexto |= {
        'yo': yo, 'donantes': donantes, 'categorias': categorias_filtradas, 'todas_categorias': todas_categorias,
        'total_donantes': Usuario.objects.filter(rol='donante').count(),
        'mis_correcciones': CorreccionDatos.objects.filter(solicitante=yo).select_related('usuario').order_by('-id'),
        'categorias_existentes': [{'id': c.id, 'nombre': c.nombre.strip().lower()} for c in todas_categorias],
        'edad_minima_nacimiento': fecha_hace_anios(14, timezone.localdate()),
        'ruta': RUTAS,
    }
    return render(request, 'core/dashboard_asistente.html', contexto)


# ── DONANTES / SOLICITANTES ───────────────────────────────────────

@rol_requerido('asistente')
@require_POST
def donante_crear(request):
    form = DonanteCrearForm(request.POST)
    if not form.is_valid():
        messages.error(request, primer_error(form))
        return a_panel(PANEL, 'donantes')
    c = form.cleaned_data
    Usuario.objects.create_user(
        email=c['email'], password=c['password'], rol='donante', estado='activo',
        nombre=c['nombre'], apellido=c['apellido'], tipo_documento=c['tipoDocumento'],
        num_documento=c['numDocumento'], fecha_nacimiento=c['fechaNacimiento'], direccion=c['direccion'],
        telefono=c['telefono'], necesidad=c['necesidad'] or None, prioridad=c['prioridad'] or None,
        observacion_visita=c['observacion_visita'] or None)
    messages.success(request, 'Donante/solicitante creado correctamente.')
    return a_panel(PANEL, 'donantes')


@rol_requerido('asistente')
@require_POST
def donante_editar(request, pk):
    donante = _donante_o_404(pk)
    form = DonanteEditarForm(request.POST, usuario=donante)
    if not form.is_valid():
        messages.error(request, primer_error(form))
        return a_panel(PANEL, 'donantes')
    c = form.cleaned_data
    donante.email, donante.telefono, donante.direccion = c['email'], c['telefono'], c['direccion']
    donante.necesidad = c['necesidad'] or None
    donante.prioridad = c['prioridad'] or None
    donante.observacion_visita = c['observacion_visita'] or None
    if c['password']:
        donante.set_password(c['password'])
    donante.save()
    messages.success(request, 'Donante/solicitante actualizado correctamente.')
    return a_panel(PANEL, 'donantes')


@rol_requerido('asistente')
@require_POST
def donante_toggle_estado(request, pk):
    donante = _donante_o_404(pk)
    donante.estado = 'inactivo' if donante.estado == 'activo' else 'activo'
    donante.save(update_fields=['estado'])
    messages.success(request, f'Donante/solicitante {donante.estado} correctamente.')
    return a_panel(PANEL, 'donantes')


@rol_requerido('asistente')
@require_GET
def donante_historial(request, pk):
    """JSON con las donaciones y solicitudes de un donante/solicitante (lo consume el modal de historial)."""
    donante = _donante_o_404(pk)
    donaciones = []
    for d in Donacion.objects.filter(donantes__donante=donante).select_related('categoria') \
            .prefetch_related(Prefetch('donantes', queryset=DonacionUsuario.objects.filter(donante=donante),
                                       to_attr='mios')).distinct().order_by('-id'):
        donaciones.append({
            'idDonacion': d.id, 'descripcion': d.descripcion, 'categoria': d.categoria.nombre if d.categoria else '—',
            'estado': d.estado, 'fecha': d.mios[0].fecha_creacion.strftime('%d/%m/%Y') if d.mios else '—'})
    solicitudes = [{
        'idSolicitud': s.id, 'descripcion': s.descripcion, 'categoria': s.categoria.nombre if s.categoria else '—',
        'estado': s.estado, 'fecha': s.fecha_creacion.strftime('%d/%m/%Y')}
        for s in Solicitud.objects.filter(solicitante=donante).select_related('categoria').order_by('-id')]
    return JsonResponse({'donaciones': donaciones, 'solicitudes': solicitudes})


@rol_requerido('asistente')
@require_POST
def donante_solicitar_correccion(request, pk):
    return procesar_correccion(
        request, _donante_o_404(pk), a_panel(PANEL, 'donantes'),
        'Solicitud de corrección enviada. Un administrador la revisará.')
