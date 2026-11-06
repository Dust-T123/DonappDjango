from django.contrib import admin
from . import models

for modelo in (
    models.Usuario,
    models.Categoria,
    models.Evento,
    models.Donacion,
    models.Solicitud,
    models.DonacionUsuario,
    models.VisitaDomiciliaria,
    models.VisitaObservacion,
    models.CorreccionDatos,
):
    admin.site.register(modelo)