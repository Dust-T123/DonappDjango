from django.core.management.base import BaseCommand

from core.hashes import normalizar_hashes
from core.models import Usuario


class Command(BaseCommand):
    help = ('Convierte las contraseñas heredadas de Laravel ($2y$...) al formato que Django reconoce '
            '(bcrypt$$2b$...). Es seguro repetirlo: solo toca los hashes que aún están crudos. '
            'Ejecútalo cada vez que importes usuarios desde Laravel.')

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true',
                            help='Solo informa cuántos hashes se convertirían, sin modificar nada.')

    def handle(self, *args, **opciones):
        dry_run = opciones['dry_run']
        r = normalizar_hashes(Usuario, dry_run=dry_run)
        verbo = 'Se convertirían' if dry_run else 'Convertidos'
        self.stdout.write(self.style.SUCCESS(f'{verbo}: {r["convertidos"]} contraseña(s) de Laravel.'))
        self.stdout.write(f'Sin cambios (ya en formato Django o sin contraseña): {r["sin_cambios"]}.')
        if r['no_reconocidos']:
            self.stderr.write(self.style.WARNING(
                f'ATENCIÓN: {len(r["no_reconocidos"])} usuario(s) con un formato de contraseña desconocido '
                f'(no podrán iniciar sesión hasta restablecerla). Ids: {r["no_reconocidos"]}'))
        if dry_run:
            self.stdout.write('Modo --dry-run: no se modificó la base de datos.')
