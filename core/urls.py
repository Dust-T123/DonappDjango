from django.urls import path

from . import views

urlpatterns = [
    # ── Públicas ─────────────────────────────────────────────────────────────
    path('', views.index, name='index'),
    path('terminos/', views.terminos, name='terminos'),

    # ── Autenticación ────────────────────────────────────────────────────────
    path('login/', views.login_view, name='login'),
    path('login/exito/', views.login_exitoso, name='login_exitoso'),
    path('logout/', views.logout_view, name='logout'),
    path('registro/', views.registro_view, name='registro'),
    path('recuperar/', views.DonappRecuperarView.as_view(), name='recuperar'),
    path('restablecer/<uidb64>/<token>/', views.DonappRestablecerView.as_view(), name='restablecer'),

    # ── Paneles por rol ──────────────────────────────────────────────────────
    # (no usamos el prefijo "admin/" porque ya lo ocupa el admin de Django)
    path('administrador/dashboard/', views.dashboard_administrador, name='dashboard_administrador'),
    path('asistente/dashboard/', views.dashboard_asistente, name='dashboard_asistente'),
    path('usuario/dashboard/', views.dashboard_usuario, name='dashboard_usuario'),

    # ── Acciones del donante (todas POST) ────────────────────────────────────
    path('usuario/donaciones/crear/', views.donacion_crear, name='usuario_donacion_crear'),
    path('usuario/donaciones/<int:pk>/editar/', views.donacion_editar, name='usuario_donacion_editar'),
    path('usuario/donaciones/<int:pk>/cancelar/', views.donacion_cancelar, name='usuario_donacion_cancelar'),
    path('usuario/solicitudes/crear/', views.solicitud_crear, name='usuario_solicitud_crear'),
    path('usuario/solicitudes/<int:pk>/editar/', views.solicitud_editar, name='usuario_solicitud_editar'),
    path('usuario/solicitudes/<int:pk>/cancelar/', views.solicitud_cancelar, name='usuario_solicitud_cancelar'),
    path('usuario/visitas/crear/', views.visita_crear, name='usuario_visita_crear'),
    path('usuario/visitas/<int:pk>/cancelar/', views.visita_cancelar, name='usuario_visita_cancelar'),
    path('usuario/visitas/<int:pk>/nota/', views.visita_nota, name='usuario_visita_nota'),
    path('usuario/perfil/', views.perfil_actualizar, name='usuario_perfil'),
    path('usuario/perfil/solicitar-correccion/', views.perfil_solicitar_correccion,
         name='usuario_perfil_correccion'),

    # ── API pública ──────────────────────────────────────────────────────────
    path('api/estadisticas', views.api_estadisticas, name='api_estadisticas'),
    path('api/eventos', views.api_eventos, name='api_eventos'),
    path('api/eventos/<int:pk>', views.api_evento, name='api_evento'),
]
