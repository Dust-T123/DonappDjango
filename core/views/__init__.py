from .api import api_estadisticas, api_evento, api_eventos  # noqa: F401
from .auth import (  # noqa: F401
    DonappRecuperarView,
    DonappRestablecerView,
    login_exitoso,
    login_view,
    logout_view,
    registro_view,
)
from .dashboards import dashboard_administrador, dashboard_asistente  # noqa: F401
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
