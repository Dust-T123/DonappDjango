from django.shortcuts import render

from ..models import Donacion, Evento, Usuario

ESTADOS_EVENTO_ACTIVO = ('publicado', 'en_curso')


def index(request):
    contexto = {
        'statsUsuarios': Usuario.objects.filter(rol='donante').count(),
        'statsDonaciones': Donacion.objects.count(),
        'statsEventos': Evento.objects.filter(estado__in=ESTADOS_EVENTO_ACTIVO).count(),
    }
    return render(request, 'core/index.html', contexto)


def terminos(request):
    return render(request, 'core/terminos.html')
