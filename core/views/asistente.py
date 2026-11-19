"""Panel del asistente (equivalente a AsisController de Laravel).

Lo que comparte con el administrador (donaciones, solicitudes, stock, eventos, visitas,
categorías y perfil) vive en `gestion.py`. Aquí queda lo exclusivo del asistente: la
gestión de "clientes" (donantes/solicitantes).

Diferencias de seguridad respecto al original:
  * Laravel permitía que un asistente editara, desactivara o pidiera correcciones sobre
    CUALQUIER usuario por id (incluidos administradores). Aquí todas las acciones sobre
    "clientes" quedan limitadas a usuarios con rol donante.
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
from ..forms import ClienteCrearForm, ClienteEditarForm
from ..models import Categoria, CorreccionDatos, Donacion, DonacionUsuario, Solicitud, Usuario
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


def _cliente_o_404(pk):
    """El asistente solo gestiona donantes/solicitantes, nunca a otro personal."""
    return get_object_or_404(Usuario, pk=pk, rol='donante')


# ── DASHBOARD ────────────────────────────────────────────────────────────────

@rol_requerido('asistente')
def dashboard_asistente(request):
    g = request.GET
    yo = request.user

    # Donantes / solicitantes
    clientes = Usuario.objects.filter(rol='donante')
    if g.get('cli_search'):
        s = g['cli_search']
        clientes = clientes.filter(Q(nombre__icontains=s) | Q(apellido__icontains=s) | Q(email__icontains=s))
    if g.get('cli_prioridad') in ORDEN_PRIORIDAD:
        clientes = clientes.filter(prioridad=g['cli_prioridad'])
    clientes = clientes.order_by(
        {'az': 'nombre', 'za': '-nombre'}.get(g.get('cli_sort'), '-id')
    ) if g.get('cli_sort') != 'prioridad' else clientes.annotate(_r=_rank_prioridad('prioridad')).order_by('_r', '-id')
    clientes = list(clientes)
    for c in clientes:
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
        'yo': yo, 'clientes': clientes, 'categorias': categorias_filtradas, 'todas_categorias': todas_categorias,
        'total_clientes': Usuario.objects.filter(rol='donante').count(),
        'mis_correcciones': CorreccionDatos.objects.filter(solicitante=yo).select_related('usuario').order_by('-id'),
        'categorias_existentes': [{'id': c.id, 'nombre': c.nombre.strip().lower()} for c in todas_categorias],
        'edad_minima_nacimiento': timezone.localdate().replace(year=timezone.localdate().year - 14),
        'ruta': RUTAS,
    }
    return render(request, 'core/dashboard_asistente.html', contexto)


# ── CLIENTES (donantes / solicitantes) ───────────────────────────────────────

@rol_requerido('asistente')
@require_POST
def cliente_crear(request):
    form = ClienteCrearForm(request.POST)
    if not form.is_valid():
        messages.error(request, primer_error(form))
        return a_panel(PANEL, 'clientes')
    c = form.cleaned_data
    Usuario.objects.create_user(
        email=c['email'], password=c['password'], rol='donante', estado='activo',
        nombre=c['nombre'], apellido=c['apellido'], tipo_documento=c['tipoDocumento'],
        num_documento=c['numDocumento'], fecha_nacimiento=c['fechaNacimiento'], direccion=c['direccion'],
        telefono=c['telefono'], necesidad=c['necesidad'] or None, prioridad=c['prioridad'] or None,
        observacion_visita=c['observacion_visita'] or None)
    messages.success(request, 'Cliente creado correctamente.')
    return a_panel(PANEL, 'clientes')


@rol_requerido('asistente')
@require_POST
def cliente_editar(request, pk):
    cliente = _cliente_o_404(pk)
    form = ClienteEditarForm(request.POST, usuario=cliente)
    if not form.is_valid():
        messages.error(request, primer_error(form))
        return a_panel(PANEL, 'clientes')
    c = form.cleaned_data
    cliente.email, cliente.telefono, cliente.direccion = c['email'], c['telefono'], c['direccion']
    cliente.necesidad = c['necesidad'] or None
    cliente.prioridad = c['prioridad'] or None
    cliente.observacion_visita = c['observacion_visita'] or None
    if c['password']:
        cliente.set_password(c['password'])
    cliente.save()
    messages.success(request, 'Cliente actualizado correctamente.')
    return a_panel(PANEL, 'clientes')


@rol_requerido('asistente')
@require_POST
def cliente_toggle_estado(request, pk):
    cliente = _cliente_o_404(pk)
    cliente.estado = 'inactivo' if cliente.estado == 'activo' else 'activo'
    cliente.save(update_fields=['estado'])
    messages.success(request, f'Cliente {cliente.estado} correctamente.')
    return a_panel(PANEL, 'clientes')


@rol_requerido('asistente')
@require_GET
def cliente_historial(request, pk):
    """JSON con las donaciones y solicitudes de un cliente (lo consume el modal de historial)."""
    cliente = _cliente_o_404(pk)
    donaciones = []
    for d in Donacion.objects.filter(donantes__donante=cliente).select_related('categoria') \
            .prefetch_related(Prefetch('donantes', queryset=DonacionUsuario.objects.filter(donante=cliente),
                                       to_attr='mios')).distinct().order_by('-id'):
        donaciones.append({
            'idDonacion': d.id, 'descripcion': d.descripcion, 'categoria': d.categoria.nombre if d.categoria else '—',
            'estado': d.estado, 'fecha': d.mios[0].fecha_creacion.strftime('%d/%m/%Y') if d.mios else '—'})
    solicitudes = [{
        'idSolicitud': s.id, 'descripcion': s.descripcion, 'categoria': s.categoria.nombre if s.categoria else '—',
        'estado': s.estado, 'fecha': s.fecha_creacion.strftime('%d/%m/%Y')}
        for s in Solicitud.objects.filter(solicitante=cliente).select_related('categoria').order_by('-id')]
    return JsonResponse({'donaciones': donaciones, 'solicitudes': solicitudes})


@rol_requerido('asistente')
@require_POST
def cliente_solicitar_correccion(request, pk):
    return procesar_correccion(
        request, _cliente_o_404(pk), a_panel(PANEL, 'clientes'),
        'Solicitud de corrección enviada. Un administrador la revisará.')
