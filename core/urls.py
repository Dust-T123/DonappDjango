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

    # ── API pública ──────────────────────────────────────────────────────────
    path('api/estadisticas', views.api_estadisticas, name='api_estadisticas'),
    path('api/eventos', views.api_eventos, name='api_eventos'),
    path('api/eventos/<int:pk>', views.api_evento, name='api_evento'),
]
