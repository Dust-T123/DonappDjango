from datetime import date

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


def fecha_hace_anios(anios, desde=None):
    """Fecha de hace `anios` años. Si `desde` es 29 de febrero y el año de destino no es
    bisiesto, devuelve el 28 de febrero (con .replace(year=...) el panel fallaba cada 29/02)."""
    desde = desde or date.today()
    try:
        return desde.replace(year=desde.year - anios)
    except ValueError:
        return desde.replace(year=desde.year - anios, day=28)
