from django import template

register = template.Library()

ETIQUETAS_CAMPO = {
    'nombre': 'Nombre', 'apellido': 'Apellido', 'tipoDocumento': 'Tipo de documento',
    'numDocumento': 'Número de documento', 'fechaNacimiento': 'Fecha de nacimiento',
}


@register.filter
def campo_legible(valor):
    """Nombre en español del campo de una corrección de datos (en la BD se guarda el identificador)."""
    return ETIQUETAS_CAMPO.get(valor, valor)
