"""API pública (sin autenticación). Misma estructura JSON que la de Laravel
para que index.js (y una futura app móvil) funcionen sin cambios."""

from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_GET

from ..models import Categoria, Donacion, Evento, Solicitud, Usuario
from .public import ESTADOS_EVENTO_ACTIVO


def _json(datos, status=200):
    return JsonResponse(datos, status=status, json_dumps_params={'ensure_ascii': False})


def _fecha(valor):
    return valor.isoformat() if valor else None


def _serializar_evento(ev):
    return {
        'id': ev.pk,
        'nombre': ev.nombre,
        'estado': ev.estado,
        'programacion': {
            'fecha_inicio': _fecha(ev.fecha_inicio),
            'fecha_fin': _fecha(ev.fecha_fin),
            'lugar': ev.lugar,
        },
        'publicacion': {
            'titulo': ev.nombre,
            'contenido': ev.contenido,
            'fecha_publicacion': _fecha(ev.fecha_publicacion),
            # URL de la imagen (en Laravel venía en base64 desde la BD).
            'imagen': ev.imagen.url if ev.imagen else None,
        },
    }


@require_GET
def api_estadisticas(request):
    datos = {
        'total_donantes': Usuario.objects.filter(rol='donante', estado='activo').count(),
        'total_donaciones': Donacion.objects.count(),
        'donaciones_aprobadas': Donacion.objects.filter(estado='aprobada').count(),
        'donaciones_pendientes': Donacion.objects.filter(estado='pendiente').count(),
        'total_solicitudes': Solicitud.objects.count(),
        'solicitudes_aprobadas': Solicitud.objects.filter(estado='aprobada').count(),
        'eventos_activos': Evento.objects.filter(estado__in=ESTADOS_EVENTO_ACTIVO).count(),
        'total_categorias': Categoria.objects.count(),
    }
    return _json({
        'success': True,
        'mensaje': 'Estadísticas generales de Donapp',
        'data': datos,
        'generado': timezone.localtime().strftime('%d/%m/%Y %H:%M:%S'),
    })


@require_GET
def api_eventos(request):
    eventos = Evento.objects.filter(estado__in=ESTADOS_EVENTO_ACTIVO).order_by('-pk')
    datos = [_serializar_evento(ev) for ev in eventos]
    return _json({'success': True, 'total': len(datos), 'data': datos})


@require_GET
def api_evento(request, pk):
    ev = Evento.objects.filter(pk=pk, estado__in=ESTADOS_EVENTO_ACTIVO).first()
    if ev is None:
        return _json({'success': False, 'mensaje': 'Evento no encontrado o inactivo'}, status=404)
    return _json({'success': True, 'data': _serializar_evento(ev)})
