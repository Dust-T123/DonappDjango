from .api import api_estadisticas, api_evento, api_eventos  # noqa: F401
from .auth import (  # noqa: F401
    DonappRecuperarView,
    DonappRestablecerView,
    login_exitoso,
    login_view,
    logout_view,
    registro_view,
)
from .dashboards import dashboard_administrador  # noqa: F401
from .public import index, terminos  # noqa: F401
from .usuario import (  # noqa: F401
    dashboard_usuario,
    donacion_cancelar,
    donacion_crear,
    donacion_editar,
    perfil_actualizar,
    perfil_solicitar_correccion,
    solicitud_cancelar,
    solicitud_crear,
    solicitud_editar,
    visita_cancelar,
    visita_crear,
    visita_nota,
)
from .asistente import (  # noqa: F401
    categoria_crear,
    categoria_editar,
    cliente_crear,
    cliente_editar,
    cliente_historial,
    cliente_solicitar_correccion,
    cliente_toggle_estado,
    dashboard_asistente,
    donacion_estado,
    evento_crear,
    evento_editar,
    evento_estado,
    perfil_confirmar_password,
    perfil_enviar_codigo,
    solicitud_estado,
    visita_estado,
)
from .asistente import perfil_actualizar as asis_perfil_actualizar  # noqa: F401
from .asistente import perfil_solicitar_correccion as asis_perfil_solicitar_correccion  # noqa: F401
from .asistente import visita_nota as asis_visita_nota  # noqa: F401
