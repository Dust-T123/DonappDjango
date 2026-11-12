from django.shortcuts import render
from .models import Evento, Donacion
from django.contrib.auth import get_user_model

User = get_user_model()

def index(request):
    eventos = Evento.objects.filter(estado='publicado')
    donaciones = Donacion.objects.filter(estado='aprobada')
    
    # Conteo para las tarjetas de estadísticas del Hero
    stats_donaciones = Donacion.objects.count()
    stats_usuarios = User.objects.count()
    stats_eventos = Evento.objects.count()

    context = {
        'eventos': eventos,
        'donaciones': donaciones,
        'statsDonaciones': stats_donaciones,
        'statsUsuarios': stats_usuarios,
        'statsEventos': stats_eventos,
    }
    
    return render(request, 'core/index.html', context)

def login_view(request):
    return render(request, 'core/login.html')