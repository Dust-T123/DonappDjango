from django.shortcuts import render
from .models import Evento, Donacion

def index(request):
    eventos = Evento.objects.filter(estado='publicado')
    donaciones = Donacion.objects.filter(estado='aprobada')
    return render(request, 'core/index.html', {
        'eventos': eventos,
        'donaciones': donaciones
    })