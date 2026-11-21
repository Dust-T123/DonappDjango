"""Panel del donante/solicitante (equivalente a UserController de Laravel).

Seguridad: cada vista filtra por request.user, así que un donante nunca puede
leer ni modificar registros de otro (en Laravel era el mismo patrón con
`idSolicitante = sesión`). Las acciones que cambian datos son solo POST
(Laravel usaba PUT/DELETE simulados con @method).
"""

import json

from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.db import transaction
from django.db.models import Count, Prefetch, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from ..decorators import rol_requerido
from ..forms import (
    DonacionForm, NotaVisitaForm, PerfilDonanteForm,
    SolicitudForm, VisitaForm,
)
from .comun import a_panel, primer_error, procesar_correccion, url_imagen
from ..models import (
    Categoria, CorreccionDatos, Donacion, DonacionUsuario, Evento, Solicitud,
    VisitaDomiciliaria, VisitaObservacion,
)

TABS = ('inicio', 'donaciones', 'solicitudes', 'visitas', 'eventos', 'perfil')
ESTADOS_FILTRO = [('pendiente', 'Pendiente'), ('aprobada', 'Aprobada'), ('rechazada', 'Rechazada'),
                  ('completada', 'Completada'), ('cancelada', 'Cancelada')]
ESTADOS_ACTIVOS_VISITA = ('pendiente', 'aprobada')


def _filtrar(queryset, request, prefijo):
    """Filtros de búsqueda / estado / categoría / orden, idénticos a los del controlador original."""
    g = request.GET
    if g.get(f'{prefijo}_buscar'):
        queryset = queryset.filter(descripcion__icontains=g[f'{prefijo}_buscar'])
    if g.get(f'{prefijo}_estado'):
        queryset = queryset.filter(estado=g[f'{prefijo}_estado'])
    cat = g.get(f'{prefijo}_cat', '')
    if cat.isdigit() and int(cat) > 0:
        queryset = queryset.filter(categoria_id=int(cat))
    orden = {'az': 'descripcion', 'za': '-descripcion'}.get(g.get(f'{prefijo}_sort'), '-id')
    return queryset.order_by(orden)


# ── DASHBOARD ────────────────────────────────────────────────────────────────

@rol_requerido('donante')
def dashboard_usuario(request):
    usuario = request.user
    tab = request.GET.get('tab', 'inicio')
    if tab not in TABS:
        tab = 'inicio'

    registro_donante = Prefetch('donantes', queryset=DonacionUsuario.objects.filter(donante=usuario),
                                to_attr='mi_registro')
    mis_donaciones = list(
        _filtrar(Donacion.objects.filter(donantes__donante=usuario).select_related('categoria')
                 .prefetch_related(registro_donante).distinct(), request, 'don'))
    for d in mis_donaciones:
        d.fecha = d.mi_registro[0].fecha_creacion if d.mi_registro else None
        d.json = json.dumps({
            'idDonacion': d.id, 'descripcion': d.descripcion,
            'categoria': d.categoria.nombre if d.categoria else '—', 'stock': d.stock,
            'estado': d.estado, 'fechaCreacion': d.fecha.isoformat() if d.fecha else '',
            'observacion': d.observacion or '', 'imagen': url_imagen(d.imagen),
            'idCategoria': d.categoria_id,
        }, ensure_ascii=False)

    mis_solicitudes = list(_filtrar(
        Solicitud.objects.filter(solicitante=usuario).select_related('categoria'), request, 'sol'))
    for s in mis_solicitudes:
        s.json = json.dumps({
            'idSolicitud': s.id, 'descripcion': s.descripcion,
            'categoria': s.categoria.nombre if s.categoria else '—', 'estado': s.estado,
            'fechaCreacion': s.fecha_creacion.date().isoformat(), 'observacion': s.observacion or '',
            'idCategoria': s.categoria_id,
        }, ensure_ascii=False)

    eventos = list(Evento.objects.filter(estado__in=('publicado', 'en_curso')).order_by('-id'))
    for ev in eventos:
        ev.multidia = bool(ev.fecha_inicio and ev.fecha_fin and ev.fecha_inicio != ev.fecha_fin)
        ev.json = json.dumps({
            'nombre': ev.nombre, 'contenido': ev.contenido, 'imagen': url_imagen(ev.imagen),
            'fechaInicio': ev.fecha_inicio.isoformat() if ev.fecha_inicio else None,
            'fechaFin': ev.fecha_fin.isoformat() if ev.fecha_fin else None,
            'lugar': ev.lugar,
            'fechaPublicacion': ev.fecha_publicacion.isoformat() if ev.fecha_publicacion else None,
        }, ensure_ascii=False)

    mis_visitas = list(
        VisitaDomiciliaria.objects.filter(usuario=usuario).select_related('gestor')
        .prefetch_related(Prefetch('observaciones',
                                   queryset=VisitaObservacion.objects.select_related('usuario').order_by('fecha')))
        .order_by('-id'))
    for v in mis_visitas:
        v.json = json.dumps({
            'idVisita': v.id, 'direccion': v.direccion,
            'historial': [{
                'autor': h.usuario.nombre if h.usuario else 'Sistema', 'texto': h.texto,
                'fecha': timezone.localtime(h.fecha).strftime('%d/%m/%Y %H:%M'),
            } for h in v.observaciones.all()],
        }, ensure_ascii=False)
    visita_activa = next((v for v in mis_visitas if v.estado in ESTADOS_ACTIVOS_VISITA), None)

    # Estadísticas en 2 consultas (en Laravel eran 6 COUNT separados).
    d = Donacion.objects.filter(donantes__donante=usuario).aggregate(
        total=Count('id', distinct=True),
        pend=Count('id', filter=Q(estado='pendiente'), distinct=True),
        apro=Count('id', filter=Q(estado='aprobada'), distinct=True))
    s = Solicitud.objects.filter(solicitante=usuario).aggregate(
        total=Count('id'), pend=Count('id', filter=Q(estado='pendiente')),
        apro=Count('id', filter=Q(estado='aprobada')))
    stats = {'total_don': d['total'], 'don_pendientes': d['pend'], 'don_aprobadas': d['apro'],
             'total_sol': s['total'], 'sol_pendientes': s['pend'], 'sol_aprobadas': s['apro']}

    return render(request, 'core/dashboard_usuario.html', {
        'usuario': usuario, 'primer_nombre': usuario.nombre.split(' ')[0], 'tab_activo': tab,
        'mis_donaciones': mis_donaciones, 'mis_solicitudes': mis_solicitudes,
        'categorias': Categoria.objects.order_by('nombre'), 'eventos': eventos,
        'mis_visitas': mis_visitas, 'visita_activa': visita_activa, 'stats': stats,
        'mis_correcciones': CorreccionDatos.objects.filter(solicitante=usuario).order_by('-id'),
        'estados_filtro': ESTADOS_FILTRO, 'hoy': timezone.localdate(),
    })


# ── DONACIONES ───────────────────────────────────────────────────────────────

@rol_requerido('donante')
@require_POST
def donacion_crear(request):
    form = DonacionForm(request.POST, request.FILES)
    if not form.is_valid():
        messages.error(request, primer_error(form))
        return a_panel('dashboard_usuario', 'donaciones')
    c = form.cleaned_data
    with transaction.atomic():
        donacion = Donacion.objects.create(
            descripcion=c['descripcion'], imagen=c['imagen'] or None, estado='pendiente',
            stock=c['stock'], categoria=c['idCategoria'])
        DonacionUsuario.objects.create(donante=request.user, donacion=donacion)
    messages.success(request, '¡Donación registrada! Queda pendiente de revisión.')
    return a_panel('dashboard_usuario', 'donaciones')


@rol_requerido('donante')
@require_POST
def donacion_editar(request, pk):
    # Solo se edita una donación propia y todavía pendiente.
    donacion = get_object_or_404(Donacion, pk=pk, donantes__donante=request.user, estado='pendiente')
    form = DonacionForm(request.POST, request.FILES)
    if not form.is_valid():
        messages.error(request, primer_error(form))
        return a_panel('dashboard_usuario', 'donaciones')
    c = form.cleaned_data
    donacion.descripcion, donacion.categoria, donacion.stock = c['descripcion'], c['idCategoria'], c['stock']
    if c['imagen']:
        donacion.imagen = c['imagen']
    donacion.save()
    messages.success(request, 'Donación actualizada correctamente.')
    return a_panel('dashboard_usuario', 'donaciones')


@rol_requerido('donante')
@require_POST
def donacion_cancelar(request, pk):
    donacion = get_object_or_404(Donacion, pk=pk, donantes__donante=request.user, estado='pendiente')
    with transaction.atomic():
        DonacionUsuario.objects.filter(donacion=donacion).delete()
        donacion.delete()
    messages.success(request, 'Donación cancelada correctamente.')
    return a_panel('dashboard_usuario', 'donaciones')


# ── SOLICITUDES ──────────────────────────────────────────────────────────────

@rol_requerido('donante')
@require_POST
def solicitud_crear(request):
    form = SolicitudForm(request.POST)
    if not form.is_valid():
        messages.error(request, primer_error(form))
        return a_panel('dashboard_usuario', 'solicitudes')
    # En Laravel idGestor se llenaba con el propio solicitante; aquí queda vacío
    # hasta que un asistente/administrador la gestione.
    Solicitud.objects.create(descripcion=form.cleaned_data['descripcion'], estado='pendiente',
                             solicitante=request.user, categoria=form.cleaned_data['idCategoria'])
    messages.success(request, '¡Solicitud registrada! Queda pendiente de revisión.')
    return a_panel('dashboard_usuario', 'solicitudes')


@rol_requerido('donante')
@require_POST
def solicitud_editar(request, pk):
    solicitud = get_object_or_404(Solicitud, pk=pk, solicitante=request.user, estado='pendiente')
    form = SolicitudForm(request.POST)
    if not form.is_valid():
        messages.error(request, primer_error(form))
        return a_panel('dashboard_usuario', 'solicitudes')
    solicitud.descripcion = form.cleaned_data['descripcion']
    solicitud.categoria = form.cleaned_data['idCategoria']
    solicitud.save()
    messages.success(request, 'Solicitud actualizada correctamente.')
    return a_panel('dashboard_usuario', 'solicitudes')


@rol_requerido('donante')
@require_POST
def solicitud_cancelar(request, pk):
    get_object_or_404(Solicitud, pk=pk, solicitante=request.user, estado='pendiente').delete()
    messages.success(request, 'Solicitud cancelada correctamente.')
    return a_panel('dashboard_usuario', 'solicitudes')


# ── VISITAS DOMICILIARIAS ────────────────────────────────────────────────────

@rol_requerido('donante')
@require_POST
def visita_crear(request):
    # Solo una visita activa (pendiente o aprobada) a la vez por usuario.
    if VisitaDomiciliaria.objects.filter(usuario=request.user, estado__in=ESTADOS_ACTIVOS_VISITA).exists():
        messages.error(request, 'Ya tienes una visita domiciliaria pendiente o aprobada. '
                                'Espera a que se resuelva o cancélala antes de solicitar otra.')
        return a_panel('dashboard_usuario', 'visitas')
    form = VisitaForm(request.POST)
    if not form.is_valid():
        messages.error(request, primer_error(form))
        return a_panel('dashboard_usuario', 'visitas')
    c = form.cleaned_data
    VisitaDomiciliaria.objects.create(usuario=request.user, direccion=c['direccion'], motivo=c['motivo'],
                                      fecha_preferida=c['fechaPreferida'], estado='pendiente')
    messages.success(request, 'Tu solicitud de visita domiciliaria fue enviada. '
                              'Un asistente o administrador la revisará pronto.')
    return a_panel('dashboard_usuario', 'visitas')


@rol_requerido('donante')
@require_POST
def visita_cancelar(request, pk):
    visita = get_object_or_404(VisitaDomiciliaria, pk=pk, usuario=request.user)
    if visita.estado != 'pendiente':
        messages.error(request, 'Solo puedes cancelar visitas que aún están pendientes.')
        return a_panel('dashboard_usuario', 'visitas')
    visita.estado, visita.fecha_resolucion = 'cancelada', timezone.now()
    visita.save()
    messages.success(request, 'Visita cancelada.')
    return a_panel('dashboard_usuario', 'visitas')


@rol_requerido('donante')
@require_POST
def visita_nota(request, pk):
    visita = get_object_or_404(VisitaDomiciliaria, pk=pk, usuario=request.user)
    form = NotaVisitaForm(request.POST)
    if not form.is_valid():
        messages.error(request, primer_error(form))
        return a_panel('dashboard_usuario', 'visitas')
    VisitaObservacion.objects.create(visita=visita, usuario=request.user, texto=form.cleaned_data['texto'])
    messages.success(request, 'Nota agregada.')
    return a_panel('dashboard_usuario', 'visitas')


# ── PERFIL ───────────────────────────────────────────────────────────────────

@rol_requerido('donante')
@require_POST
def perfil_actualizar(request):
    usuario = request.user
    form = PerfilDonanteForm(request.POST, usuario=usuario)
    if not form.is_valid():
        messages.error(request, primer_error(form))
        return a_panel('dashboard_usuario', 'perfil')
    c = form.cleaned_data
    usuario.email, usuario.telefono, usuario.direccion = c['email'], c['telefono'], c['direccion']
    usuario.necesidad = c['necesidad'] or None
    if c['password']:
        usuario.set_password(c['password'])
    usuario.save()
    if c['password']:
        update_session_auth_hash(request, usuario)  # mantiene la sesión abierta tras cambiar la clave
    messages.success(request, 'Perfil actualizado correctamente.')
    return a_panel('dashboard_usuario', 'perfil')


@rol_requerido('donante')
@require_POST
def perfil_solicitar_correccion(request):
    return procesar_correccion(
        request, request.user, a_panel('dashboard_usuario', 'perfil'),
        'Tu solicitud de corrección fue enviada y quedará pendiente de aprobación por un administrador.')
