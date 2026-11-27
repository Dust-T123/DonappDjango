"""Gestión compartida por asistente y administrador.

Donaciones, solicitudes, stock, eventos, visitas, categorías y perfil propio se
comportan igual para ambos roles: una sola implementación, probada una vez. Tras
cada acción se vuelve al panel del rol de quien la hizo.
"""

import hashlib
import hmac
import json
import secrets
import time

from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.db import transaction
from django.db.models import Case, Count, IntegerField, Prefetch, Q, Sum, Value, When
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.views.decorators.http import require_POST

from ..decorators import rol_requerido
from ..forms import (
    CategoriaForm, ConfirmarPasswordForm, EstadoEventoForm, EstadoGestionForm,
    EstadoVisitaForm, EventoForm, NotaVisitaForm, PerfilPersonalForm,
)
from ..models import (
    ESTADOS_DONACION, ESTADOS_EVENTO, ESTADOS_VISITA,
    Categoria, Donacion, DonacionUsuario, Evento, Solicitud, VisitaDomiciliaria, VisitaObservacion,
)
from ..notificaciones import enviar_codigo_password, notificar_estado
from ..utils import PANEL_POR_ROL
from .comun import a_panel, primer_error, procesar_correccion, url_imagen

ESTADOS_FINALES_VISITA = ('rechazada', 'realizada', 'cancelada')
# Una donación o solicitud cancelada queda en el historial como constancia: no se reabre.
ESTADO_CANCELADO = 'cancelada'
ORDEN_PRIORIDAD = {'urgente': 0, 'alta': 1, 'media': 2, 'baja': 3}
CODIGO_VIGENCIA_SEG = 10 * 60
CODIGO_MAX_INTENTOS = 5


def _panel(request, tab):
    """Vuelve al panel del rol de quien hizo la acción, en la pestaña indicada."""
    return a_panel(PANEL_POR_ROL[request.user.rol], tab)


def _rank_prioridad(campo):
    """Orden urgente -> baja, con los que no tienen prioridad al final (FIELD(...) de MySQL)."""
    return Case(*[When(**{campo: k}, then=Value(v)) for k, v in ORDEN_PRIORIDAD.items()],
                default=Value(99), output_field=IntegerField())


def _etiquetas(estados):
    """[('en_curso', 'en_curso')] -> [('en_curso', 'En curso')] para los selectores."""
    return [(v, v.replace('_', ' ').capitalize()) for v, _ in estados]


def _entero(valor):
    return int(valor) if valor and valor.isdigit() and int(valor) > 0 else None


def _iso(valor):
    return valor.isoformat() if valor else ''


def datos_gestion(request):
    """Datos de las pestañas que el asistente y el administrador comparten:
    donaciones, solicitudes, stock, eventos, visitas y reportes (con sus filtros)."""
    g = request.GET
    # Donaciones
    registros = Prefetch('donantes', queryset=DonacionUsuario.objects.select_related('donante').order_by('id'),
                         to_attr='registros')
    donaciones = Donacion.objects.select_related('categoria').prefetch_related(registros)
    if g.get('don_search'):
        s = g['don_search']
        donaciones = donaciones.filter(Q(descripcion__icontains=s) | Q(donantes__donante__nombre__icontains=s))
    if g.get('don_estado'):
        donaciones = donaciones.filter(estado=g['don_estado'])
    if _entero(g.get('don_cat')):
        donaciones = donaciones.filter(categoria_id=_entero(g['don_cat']))
    donaciones = list(donaciones.distinct().order_by(
        {'az': 'descripcion', 'za': '-descripcion'}.get(g.get('don_sort'), '-id')))
    for d in donaciones:
        primero = d.registros[0] if d.registros else None
        d.donante_nombre = primero.donante.nombre if primero and primero.donante else None
        d.fecha = primero.fecha_creacion if primero else None
        d.json = json.dumps({
            'idDonacion': d.id, 'descripcion': d.descripcion, 'estado': d.estado,
            'observacion': d.observacion or '', 'donante': d.donante_nombre,
            'categoria': d.categoria.nombre if d.categoria else None, 'stock': d.stock,
            'fechaCreacion': _iso(d.fecha), 'imagen': url_imagen(d.imagen),
        }, ensure_ascii=False)

    # Inventario: donaciones aprobadas agrupadas por artículo
    inventario = Donacion.objects.filter(estado='aprobada')
    if g.get('inv_search'):
        inventario = inventario.filter(descripcion__icontains=g['inv_search'])
    if _entero(g.get('inv_cat')):
        inventario = inventario.filter(categoria_id=_entero(g['inv_cat']))
    inventario = list(
        inventario.values('descripcion', 'categoria__nombre')
        .annotate(total_stock=Sum('stock'), num_donaciones=Count('id'))
        .order_by(*{'az': ('descripcion',), 'za': ('-descripcion',)}.get(g.get('inv_sort'), ('-total_stock', 'descripcion'))))
    total_unidades = sum(i['total_stock'] or 0 for i in inventario)
    for i in inventario:
        i['json'] = json.dumps({'articulo': i['descripcion'], 'categoria': i['categoria__nombre'] or '—',
                                'cantidad': i['total_stock'] or 0, 'donaciones': i['num_donaciones']}, ensure_ascii=False)

    # Solicitudes
    solicitudes = Solicitud.objects.select_related('categoria', 'solicitante', 'gestor')
    if g.get('sol_search'):
        s = g['sol_search']
        solicitudes = solicitudes.filter(Q(descripcion__icontains=s) | Q(solicitante__nombre__icontains=s))
    if g.get('sol_estado'):
        solicitudes = solicitudes.filter(estado=g['sol_estado'])
    if _entero(g.get('sol_cat')):
        solicitudes = solicitudes.filter(categoria_id=_entero(g['sol_cat']))
    if g.get('sol_sort') == 'prioridad':
        solicitudes = solicitudes.annotate(_r=_rank_prioridad('solicitante__prioridad')).order_by('_r', '-id')
    else:
        solicitudes = solicitudes.order_by('descripcion' if g.get('sol_sort') == 'az' else '-id')
    solicitudes = list(solicitudes)
    for s in solicitudes:
        s.json = json.dumps({
            'idSolicitud': s.id, 'descripcion': s.descripcion, 'estado': s.estado,
            'observacion': s.observacion or '', 'solicitante': s.solicitante.nombre if s.solicitante else None,
            'prioridad': s.solicitante.prioridad if s.solicitante else None,
            # el JS del administrador usa estas dos claves
            'nombre_solicitante': s.solicitante.nombre if s.solicitante else None,
            'nombre_gestor': s.gestor.nombre if s.gestor else None,
            'categoria': s.categoria.nombre if s.categoria else None,
            'fechaCreacion': s.fecha_creacion.date().isoformat(),
        }, ensure_ascii=False)

    # Eventos
    eventos = Evento.objects.all()
    if g.get('ev_search'):
        eventos = eventos.filter(nombre__icontains=g['ev_search'])
    if g.get('ev_estado'):
        eventos = eventos.filter(estado=g['ev_estado'])
    eventos = list(eventos.order_by({'az': 'nombre', 'za': '-nombre'}.get(g.get('ev_sort'), '-id')))
    for ev in eventos:
        ev.multidia = bool(ev.fecha_inicio and ev.fecha_fin and ev.fecha_inicio != ev.fecha_fin)
        ev.json = json.dumps({
            'idEvento': ev.id, 'Nombre': ev.nombre, 'estado': ev.estado,
            'fecha_inicio': _iso(ev.fecha_inicio), 'fecha_fin': _iso(ev.fecha_fin),
            'lugar_entrega': ev.lugar or '', 'titulo_pub': ev.nombre, 'contenido_pub': ev.contenido or '',
            'imagen': url_imagen(ev.imagen) or None,
        }, ensure_ascii=False)

    # Visitas domiciliarias
    visitas = VisitaDomiciliaria.objects.select_related('usuario', 'gestor').prefetch_related(
        Prefetch('observaciones', queryset=VisitaObservacion.objects.select_related('usuario').order_by('fecha', 'id')))
    if g.get('vis_estado'):
        visitas = visitas.filter(estado=g['vis_estado'])
    if g.get('vis_sort') == 'az':
        visitas = visitas.order_by('usuario__nombre', '-id')
    else:
        visitas = visitas.annotate(_p=Case(When(estado='pendiente', then=Value(0)), default=Value(1),
                                           output_field=IntegerField())).order_by('_p', '-id')
    visitas = list(visitas)
    for v in visitas:
        notas = list(v.observaciones.all())
        v.ultima_nota = notas[-1].texto if notas else None
        v.editable = v.estado in ('pendiente', 'aprobada')
        v.json = json.dumps({
            'idVisita': v.id, 'estado': v.estado, 'usuario': v.usuario.nombre if v.usuario else None,
            'editable': v.editable,
            # información completa para el detalle (el texto largo se recorta en la tabla)
            'direccion': v.direccion, 'motivo': v.motivo, 'observacion': v.observacion or '',
            'fechaPreferida': v.fecha_preferida.strftime('%d/%m/%Y') if v.fecha_preferida else None,
            'fechaSolicitud': timezone.localtime(v.fecha_solicitud).strftime('%d/%m/%Y %H:%M'),
            'fechaResolucion': (timezone.localtime(v.fecha_resolucion).strftime('%d/%m/%Y %H:%M')
                                if v.fecha_resolucion else None),
            'gestor': v.gestor.nombre if v.gestor else None,
            'historial': [{'autor': h.usuario.nombre if h.usuario else 'Sistema', 'texto': h.texto,
                           'fecha': timezone.localtime(h.fecha).strftime('%d/%m/%Y %H:%M')} for h in notas],
        }, ensure_ascii=False)

    # Datos para los reportes PDF (los filtra el JS en el navegador)
    reporte_donaciones = [{
        'idDonacion': d.id, 'descripcion': d.descripcion, 'categoria': d.categoria.nombre if d.categoria else '—',
        'stock': d.stock, 'estado': d.estado, 'donante': d.donante_nombre or '—',
        'fechaCreacion': _iso(d.fecha) or None, 'observacion': d.observacion or '',
    } for d in Donacion.objects.select_related('categoria').prefetch_related(registros).order_by('-id')
        for d in [_con_primer_donante(d)]]
    reporte_solicitudes = [{
        'idSolicitud': s.id, 'descripcion': s.descripcion, 'categoria': s.categoria.nombre if s.categoria else '—',
        'estado': s.estado, 'solicitante': s.solicitante.nombre if s.solicitante else '—',
        'fechaCreacion': s.fecha_creacion.date().isoformat(), 'observacion': s.observacion or '',
    } for s in Solicitud.objects.select_related('categoria', 'solicitante').order_by('-id')]

    return {
        'donaciones': donaciones, 'solicitudes': solicitudes, 'eventos': eventos, 'visitas': visitas,
        'inventario': inventario, 'total_unidades_inventario': total_unidades,
        'reporte_donaciones': reporte_donaciones, 'reporte_solicitudes': reporte_solicitudes,
        'estados_gestion': _etiquetas(ESTADOS_DONACION), 'estados_evento': _etiquetas(ESTADOS_EVENTO),
        'estados_visita': _etiquetas(ESTADOS_VISITA),
        # La pestaña interna "Solicitudes" se abre sola cuando se está filtrando por solicitudes.
        'ver_sol': bool(g.get('sol_search') or g.get('sol_estado')),
        'total_pendientes': Donacion.objects.filter(estado='pendiente').count()
                            + Solicitud.objects.filter(estado='pendiente').count(),
        'total_donaciones': Donacion.objects.count(), 'total_solicitudes': Solicitud.objects.count(),
        'total_aprobadas': Donacion.objects.filter(estado='aprobada').count(),
        'total_eventos': Evento.objects.count(),
        'total_visitas_pendientes': VisitaDomiciliaria.objects.filter(estado='pendiente').count(),
        'hoy': timezone.localdate(),
    }

def _con_primer_donante(d):
    primero = d.registros[0] if d.registros else None
    d.donante_nombre = primero.donante.nombre if primero and primero.donante else None
    d.fecha = primero.fecha_creacion if primero else None
    return d


# ── CATEGORÍAS ───────────────────────────────────────────────────────────────

@rol_requerido('asistente', 'administrador')
@require_POST
def categoria_crear(request):
    form = CategoriaForm(request.POST)
    if not form.is_valid():
        messages.error(request, primer_error(form))
        return _panel(request, 'categorias')
    Categoria.objects.create(nombre=form.cleaned_data['nombre_categoria'], creado_por=request.user)
    messages.success(request, 'Categoría creada.')
    return _panel(request, 'categorias')


@rol_requerido('asistente', 'administrador')
@require_POST
def categoria_editar(request, pk):
    categoria = get_object_or_404(Categoria, pk=pk)
    form = CategoriaForm(request.POST, excluir_pk=categoria.pk)
    if not form.is_valid():
        messages.error(request, primer_error(form))
        return _panel(request, 'categorias')
    categoria.nombre = form.cleaned_data['nombre_categoria']
    categoria.save()
    messages.success(request, 'Categoría actualizada.')
    return _panel(request, 'categorias')


# ── EVENTOS ──────────────────────────────────────────────────────────────────

@rol_requerido('asistente', 'administrador')
@require_POST
def evento_crear(request):
    form = EventoForm(request.POST, request.FILES, nuevo=True)
    if not form.is_valid():
        messages.error(request, primer_error(form))
        return _panel(request, 'eventos')
    c = form.cleaned_data
    Evento.objects.create(
        nombre=c['titulo_pub'] or c['nombre_evento'], contenido=c['contenido_pub'], imagen=c['imagen_pub'] or None,
        fecha_publicacion=timezone.localdate(), fecha_inicio=c['fecha_inicio'], fecha_fin=c['fecha_fin'],
        lugar=c['lugar_entrega'], estado=c['estado_evento'] or 'borrador')
    messages.success(request, 'Evento creado.')
    return _panel(request, 'eventos')


@rol_requerido('asistente', 'administrador')
@require_POST
def evento_editar(request, pk):
    evento = get_object_or_404(Evento, pk=pk)
    form = EventoForm(request.POST, request.FILES, nuevo=False)
    if not form.is_valid():
        messages.error(request, primer_error(form))
        return _panel(request, 'eventos')
    c = form.cleaned_data
    evento.nombre, evento.contenido = c['titulo_pub'] or c['nombre_evento'], c['contenido_pub']
    evento.fecha_inicio, evento.fecha_fin, evento.lugar = c['fecha_inicio'], c['fecha_fin'], c['lugar_entrega']
    evento.estado = c['estado_evento'] or evento.estado
    if c['imagen_pub']:
        evento.imagen = c['imagen_pub']
    evento.save()
    messages.success(request, 'Evento actualizado.')
    return _panel(request, 'eventos')


@rol_requerido('asistente', 'administrador')
@require_POST
def evento_estado(request, pk):
    evento = get_object_or_404(Evento, pk=pk)
    form = EstadoEventoForm(request.POST)
    if not form.is_valid():
        messages.error(request, primer_error(form))
        return _panel(request, 'eventos')
    evento.estado = form.cleaned_data['estado']
    evento.save(update_fields=['estado'])
    messages.success(request, 'Estado del evento actualizado a: '
                              + evento.estado.replace('_', ' ').capitalize())
    return _panel(request, 'eventos')


# ── DONACIONES / SOLICITUDES ─────────────────────────────────────────────────

@rol_requerido('asistente', 'administrador')
@require_POST
def donacion_estado(request, pk):
    donacion = get_object_or_404(Donacion, pk=pk)
    form = EstadoGestionForm(request.POST)
    if not form.is_valid():
        messages.error(request, primer_error(form))
        return _panel(request, 'donapp')
    if donacion.estado == ESTADO_CANCELADO:
        messages.error(request, 'Esta donación está cancelada y queda como constancia en el historial; '
                                'no se puede modificar su estado.')
        return _panel(request, 'donapp')
    donacion.estado = form.cleaned_data['estado']
    donacion.observacion = form.cleaned_data['observacion'] or None
    donacion.save(update_fields=['estado', 'observacion'])
    registro = DonacionUsuario.objects.filter(donacion=donacion, donante__isnull=False) \
        .select_related('donante').order_by('id').first()
    if registro:
        notificar_estado(registro.donante, 'donación', donacion.estado, donacion.observacion or '')
    messages.success(request, 'Estado actualizado.')
    return _panel(request, 'donapp')


@rol_requerido('asistente', 'administrador')
@require_POST
def solicitud_estado(request, pk):
    solicitud = get_object_or_404(Solicitud.objects.select_related('solicitante'), pk=pk)
    form = EstadoGestionForm(request.POST)
    if not form.is_valid():
        messages.error(request, primer_error(form))
        return _panel(request, 'donapp')
    if solicitud.estado == ESTADO_CANCELADO:
        messages.error(request, 'Esta solicitud está cancelada y queda como constancia en el historial; '
                                'no se puede modificar su estado.')
        return _panel(request, 'donapp')
    solicitud.estado = form.cleaned_data['estado']
    solicitud.observacion = form.cleaned_data['observacion'] or None
    solicitud.gestor = request.user
    solicitud.save(update_fields=['estado', 'observacion', 'gestor'])
    if solicitud.solicitante:
        notificar_estado(solicitud.solicitante, 'solicitud', solicitud.estado, solicitud.observacion or '')
    messages.success(request, 'Estado actualizado.')
    return _panel(request, 'donapp')


# ── VISITAS DOMICILIARIAS ────────────────────────────────────────────────────

@rol_requerido('asistente', 'administrador')
@require_POST
def visita_estado(request, pk):
    visita = get_object_or_404(VisitaDomiciliaria.objects.select_related('usuario'), pk=pk)
    form = EstadoVisitaForm(request.POST)
    if not form.is_valid():
        messages.error(request, primer_error(form))
        return _panel(request, 'visitas')
    # Una visita finalizada queda como constancia: solo admite notas de bitácora.
    if visita.estado in ESTADOS_FINALES_VISITA:
        messages.error(request, 'Esta visita ya fue finalizada y no se puede modificar su estado.')
        return _panel(request, 'visitas')
    c = form.cleaned_data
    with transaction.atomic():
        visita.estado, visita.gestor, visita.fecha_resolucion = c['estado'], request.user, timezone.now()
        visita.save(update_fields=['estado', 'gestor', 'fecha_resolucion'])
        if c['observacion']:
            VisitaObservacion.objects.create(visita=visita, usuario=request.user, texto=c['observacion'])
            if visita.usuario.rol == 'donante':
                visita.usuario.observacion_visita = c['observacion']
                visita.usuario.save(update_fields=['observacion_visita'])
    notificar_estado(visita.usuario, 'visita domiciliaria', c['estado'], c['observacion'])
    messages.success(request, 'Estado de la visita actualizado.')
    return _panel(request, 'visitas')


@rol_requerido('asistente', 'administrador')
@require_POST
def visita_nota(request, pk):
    visita = get_object_or_404(VisitaDomiciliaria.objects.select_related('usuario'), pk=pk)
    form = NotaVisitaForm(request.POST)
    if not form.is_valid():
        messages.error(request, primer_error(form))
        return _panel(request, 'visitas')
    with transaction.atomic():
        VisitaObservacion.objects.create(visita=visita, usuario=request.user, texto=form.cleaned_data['texto'])
        if visita.usuario.rol == 'donante':
            visita.usuario.observacion_visita = form.cleaned_data['texto']
            visita.usuario.save(update_fields=['observacion_visita'])
    messages.success(request, 'Nota agregada a la bitácora.')
    return _panel(request, 'visitas')


# ── PERFIL PROPIO ────────────────────────────────────────────────────────────

@rol_requerido('asistente', 'administrador')
@require_POST
def perfil_actualizar(request):
    form = PerfilPersonalForm(request.POST, usuario=request.user)
    if not form.is_valid():
        messages.error(request, primer_error(form))
        return _panel(request, 'perfil')
    c = form.cleaned_data
    request.user.email, request.user.telefono, request.user.direccion = c['email'], c['telefono'], c['direccion']
    request.user.save()
    messages.success(request, 'Perfil actualizado.')
    return _panel(request, 'perfil')


@rol_requerido('asistente', 'administrador')
@require_POST
def perfil_solicitar_correccion(request):
    return procesar_correccion(
        request, request.user, _panel(request, 'perfil'),
        'Solicitud de corrección enviada. Otro administrador la revisará.'
        if request.user.rol == 'administrador' else 'Solicitud de corrección enviada. Un administrador la revisará.')


def _hash_codigo(codigo):
    return hashlib.sha256(codigo.encode()).hexdigest()


@rol_requerido('asistente', 'administrador')
@require_POST
def perfil_enviar_codigo(request):
    """PASO 1: envía un código de 6 dígitos al correo del propio asistente."""
    codigo = str(secrets.randbelow(900000) + 100000)
    request.session['pw_codigo'] = {'hash': _hash_codigo(codigo), 'expira': time.time() + CODIGO_VIGENCIA_SEG,
                                    'intentos': 0}
    try:
        enviar_codigo_password(request.user, codigo)
    except Exception:
        request.session.pop('pw_codigo', None)
        messages.error(request, 'No se pudo enviar el código. Verifica la configuración de correo.')
        return _panel(request, 'perfil')
    messages.success(request, 'Te enviamos un código a tu correo. Ingrésalo junto con tu nueva '
                              'contraseña para confirmar el cambio.')
    return _panel(request, 'perfil')


@rol_requerido('asistente', 'administrador')
@require_POST
def perfil_confirmar_password(request):
    """PASO 2: verifica el código y aplica la nueva contraseña."""
    form = ConfirmarPasswordForm(request.POST, usuario=request.user)
    if not form.is_valid():
        messages.error(request, primer_error(form))
        return _panel(request, 'perfil')
    pendiente = request.session.get('pw_codigo')
    if not pendiente or time.time() > pendiente['expira'] or pendiente['intentos'] >= CODIGO_MAX_INTENTOS:
        request.session.pop('pw_codigo', None)
        messages.error(request, 'El código es incorrecto o ya expiró. Solicita uno nuevo.')
        return _panel(request, 'perfil')
    if not hmac.compare_digest(pendiente['hash'], _hash_codigo(form.cleaned_data['codigo'])):
        pendiente['intentos'] += 1
        request.session['pw_codigo'] = pendiente
        messages.error(request, 'El código es incorrecto o ya expiró. Solicita uno nuevo.')
        return _panel(request, 'perfil')
    request.user.set_password(form.cleaned_data['password'])
    request.user.save()
    update_session_auth_hash(request, request.user)
    request.session.pop('pw_codigo', None)
    messages.success(request, 'Contraseña actualizada correctamente.')
    return _panel(request, 'perfil')
