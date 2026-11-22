from django.urls import path

from . import views
from .decorators import rol_requerido

# Las vistas de gestión compartidas admiten ambos roles; cada panel exige el suyo en su URL.
solo_asistente = rol_requerido('asistente')
solo_administrador = rol_requerido('administrador')

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

    # ── Acciones del administrador (todas POST salvo el soporte, que es GET) ──
    path('administrador/usuarios/crear/', views.usuario_crear, name='adm_usuario_crear'),
    path('administrador/usuarios/<int:pk>/editar/', views.usuario_editar, name='adm_usuario_editar'),
    path('administrador/usuarios/<int:pk>/estado/', views.usuario_toggle_estado, name='adm_usuario_estado'),
    path('administrador/usuarios/<int:pk>/solicitar-correccion/', views.usuario_solicitar_correccion,
         name='adm_usuario_correccion'),
    path('administrador/correcciones/<int:pk>/aprobar/', views.correccion_aprobar, name='adm_correccion_aprobar'),
    path('administrador/correcciones/<int:pk>/rechazar/', views.correccion_rechazar, name='adm_correccion_rechazar'),
    path('administrador/correcciones/<int:pk>/soporte/', views.correccion_soporte, name='adm_correccion_soporte'),
    path('administrador/categorias/crear/', solo_administrador(views.categoria_crear), name='adm_categoria_crear'),
    path('administrador/categorias/<int:pk>/editar/', solo_administrador(views.categoria_editar), name='adm_categoria_editar'),
    path('administrador/categorias/<int:pk>/eliminar/', views.categoria_eliminar, name='adm_categoria_eliminar'),
    path('administrador/eventos/crear/', solo_administrador(views.evento_crear), name='adm_evento_crear'),
    path('administrador/eventos/<int:pk>/editar/', solo_administrador(views.evento_editar), name='adm_evento_editar'),
    path('administrador/eventos/<int:pk>/estado/', solo_administrador(views.evento_estado), name='adm_evento_estado'),
    path('administrador/eventos/<int:pk>/eliminar/', views.evento_eliminar, name='adm_evento_eliminar'),
    path('administrador/donaciones/<int:pk>/estado/', solo_administrador(views.donacion_estado), name='adm_donacion_estado'),
    path('administrador/solicitudes/<int:pk>/estado/', solo_administrador(views.solicitud_estado), name='adm_solicitud_estado'),
    path('administrador/visitas/<int:pk>/estado/', solo_administrador(views.visita_estado), name='adm_visita_estado'),
    path('administrador/visitas/<int:pk>/nota/', solo_administrador(views.gestion_visita_nota), name='adm_visita_nota'),
    path('administrador/perfil/', solo_administrador(views.gestion_perfil_actualizar), name='adm_perfil'),
    path('administrador/perfil/solicitar-correccion/', solo_administrador(views.gestion_perfil_solicitar_correccion),
         name='adm_perfil_correccion'),
    path('administrador/perfil/password/enviar-codigo/', solo_administrador(views.perfil_enviar_codigo), name='adm_password_enviar'),
    path('administrador/perfil/password/confirmar/', solo_administrador(views.perfil_confirmar_password),
         name='adm_password_confirmar'),
    path('asistente/dashboard/', views.dashboard_asistente, name='dashboard_asistente'),

    # ── Acciones del asistente (todas POST salvo el historial, que devuelve JSON) ──
    path('asistente/categorias/crear/', solo_asistente(views.categoria_crear), name='asis_categoria_crear'),
    path('asistente/categorias/<int:pk>/editar/', solo_asistente(views.categoria_editar), name='asis_categoria_editar'),
    path('asistente/eventos/crear/', solo_asistente(views.evento_crear), name='asis_evento_crear'),
    path('asistente/eventos/<int:pk>/editar/', solo_asistente(views.evento_editar), name='asis_evento_editar'),
    path('asistente/eventos/<int:pk>/estado/', solo_asistente(views.evento_estado), name='asis_evento_estado'),
    path('asistente/donaciones/<int:pk>/estado/', solo_asistente(views.donacion_estado), name='asis_donacion_estado'),
    path('asistente/solicitudes/<int:pk>/estado/', solo_asistente(views.solicitud_estado), name='asis_solicitud_estado'),
    path('asistente/donantes/crear/', views.donante_crear, name='asis_donante_crear'),
    path('asistente/donantes/<int:pk>/editar/', views.donante_editar, name='asis_donante_editar'),
    path('asistente/donantes/<int:pk>/estado/', views.donante_toggle_estado, name='asis_donante_estado'),
    path('asistente/donantes/<int:pk>/historial/', views.donante_historial, name='asis_donante_historial'),
    path('asistente/donantes/<int:pk>/solicitar-correccion/', views.donante_solicitar_correccion,
         name='asis_donante_correccion'),
    path('asistente/visitas/<int:pk>/estado/', solo_asistente(views.visita_estado), name='asis_visita_estado'),
    path('asistente/visitas/<int:pk>/nota/', solo_asistente(views.gestion_visita_nota), name='asis_visita_nota'),
    path('asistente/perfil/', solo_asistente(views.gestion_perfil_actualizar), name='asis_perfil'),
    path('asistente/perfil/solicitar-correccion/', solo_asistente(views.gestion_perfil_solicitar_correccion),
         name='asis_perfil_correccion'),
    path('asistente/perfil/password/enviar-codigo/', solo_asistente(views.perfil_enviar_codigo), name='asis_password_enviar'),
    path('asistente/perfil/password/confirmar/', solo_asistente(views.perfil_confirmar_password), name='asis_password_confirmar'),
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
