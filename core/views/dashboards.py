"""Paneles por rol. Por ahora son marcadores de posición: aquí se irán
migrando los dashboards de Laravel (usuario -> asistente -> administrador)."""

from django.shortcuts import render

from ..decorators import rol_requerido


def _panel(request, titulo):
    return render(request, 'core/dashboard_placeholder.html', {'titulo': titulo})


@rol_requerido('administrador')
def dashboard_administrador(request):
    return _panel(request, 'Panel del Administrador')


@rol_requerido('asistente')
def dashboard_asistente(request):
    return _panel(request, 'Panel del Asistente')


@rol_requerido('donante')
def dashboard_usuario(request):
    return _panel(request, 'Panel del Donante')
