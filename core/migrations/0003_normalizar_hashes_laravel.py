from django.db import migrations

from core.hashes import normalizar_hashes


def convertir(apps, schema_editor):
    """Si la BD ya trae usuarios importados de Laravel, deja sus contraseñas en formato Django.
    Si los usuarios se importan DESPUÉS de migrar, hay que correr:
        python manage.py normalizar_hashes_laravel"""
    normalizar_hashes(apps.get_model('core', 'Usuario'))


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0002_estados_solicitud_constraints'),
    ]

    operations = [
        # Reversa vacía: volver a $2y$ no es necesario (Django lee ambos formatos).
        migrations.RunPython(convertir, migrations.RunPython.noop),
    ]
