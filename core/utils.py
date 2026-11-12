from django.urls import reverse

# Nombre de la ruta del panel de cada rol.
PANEL_POR_ROL = {
    'administrador': 'dashboard_administrador',
    'asistente': 'dashboard_asistente',
    'donante': 'dashboard_usuario',
}


def ruta_por_rol(usuario):
    """URL del panel que le corresponde al usuario según su rol."""
    return reverse(PANEL_POR_ROL.get(usuario.rol, 'dashboard_usuario'))
