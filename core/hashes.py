"""Compatibilidad con las contraseñas heredadas de Laravel.

Laravel guarda los hashes de bcrypt "crudos": `$2y$10$...`. Django solo reconoce un hash
si empieza por el nombre de su algoritmo y un `$`, es decir `bcrypt$$2b$10$...`. Un hash
crudo NO se reconoce: `check_password()` falla siempre y nadie puede iniciar sesión (el
formulario de recuperar contraseña sí los encuentra: Django solo descarta las que empiezan por "!").

Convertirlo es solo un cambio de representación: el algoritmo, el coste y la sal son los
mismos, así que la contraseña de cada usuario sigue valiendo. `$2y$` y `$2b$` son el mismo
algoritmo (PHP y OpenBSD usan etiquetas distintas desde la corrección de un fallo de 2011).
Después, en el primer inicio de sesión de cada usuario, Django vuelve a hashear su
contraseña con el hasher preferido (PBKDF2) sin que él lo note.
"""

import re

from django.contrib.auth.hashers import identify_hasher
from django.db import transaction

# $2a$ / $2b$ / $2y$ + coste de 2 dígitos + 22 caracteres de sal + 31 de hash = 53 caracteres.
BCRYPT_CRUDO = re.compile(r'^\$2[aby]\$(\d{2})\$([./A-Za-z0-9]{53})$')


def a_formato_django(almacenado):
    """'$2y$10$...' -> 'bcrypt$$2b$10$...'. Devuelve None si no es un hash bcrypt crudo."""
    coincide = BCRYPT_CRUDO.match(almacenado or '')
    return f'bcrypt$$2b${coincide.group(1)}${coincide.group(2)}' if coincide else None


def normalizar_hashes(modelo, *, dry_run=False, lote=500):
    """Convierte a formato Django todos los hashes bcrypt crudos. Es idempotente.

    No usa `save()` a propósito: así no se ejecutan validaciones sobre datos antiguos y solo
    cambia la columna de la contraseña. Nunca devuelve ni registra hashes, solo ids.

    Devuelve {'convertidos': int, 'sin_cambios': int, 'no_reconocidos': [ids]}.
    """
    resultado = {'convertidos': 0, 'sin_cambios': 0, 'no_reconocidos': []}
    pendientes = []

    with transaction.atomic():
        for usuario in modelo.objects.only('id', 'password').order_by('id').iterator(chunk_size=lote):
            nuevo = a_formato_django(usuario.password)
            if nuevo:
                usuario.password = nuevo
                pendientes.append(usuario)
                resultado['convertidos'] += 1
                if not dry_run and len(pendientes) >= lote:
                    modelo.objects.bulk_update(pendientes, ['password'])
                    pendientes = []
                continue
            try:
                identify_hasher(usuario.password)
                resultado['sin_cambios'] += 1
            except ValueError:
                # Contraseña inutilizable ("!...") u otro formato desconocido: no se toca.
                if usuario.password.startswith('!'):
                    resultado['sin_cambios'] += 1
                else:
                    resultado['no_reconocidos'].append(usuario.id)
        if pendientes and not dry_run:
            modelo.objects.bulk_update(pendientes, ['password'])
    return resultado
