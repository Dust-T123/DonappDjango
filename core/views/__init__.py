from .api import api_estadisticas, api_evento, api_eventos  # noqa: F401
from .auth import (  # noqa: F401
    DonappRecuperarView,
    DonappRestablecerView,
    login_exitoso,
    login_view,
    logout_view,
    registro_view,
)
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
    donante_crear,
    donante_editar,
    donante_historial,
    donante_solicitar_correccion,
    donante_toggle_estado,
    dashboard_asistente,
)
from .gestion import (  # noqa: F401
    categoria_crear,
    categoria_editar,
    donacion_estado,
    evento_crear,
    evento_editar,
    evento_estado,
    perfil_confirmar_password,
    perfil_enviar_codigo,
    solicitud_estado,
    visita_estado,
)
from .gestion import perfil_actualizar as gestion_perfil_actualizar  # noqa: F401
from .gestion import perfil_solicitar_correccion as gestion_perfil_solicitar_correccion  # noqa: F401
from .gestion import visita_nota as gestion_visita_nota  # noqa: F401
from .administrador import (  # noqa: F401
    categoria_eliminar,
    correccion_aprobar,
    correccion_rechazar,
    correccion_soporte,
    dashboard_administrador,
    evento_eliminar,
    usuario_crear,
    usuario_editar,
    usuario_solicitar_correccion,
    usuario_toggle_estado,
)
