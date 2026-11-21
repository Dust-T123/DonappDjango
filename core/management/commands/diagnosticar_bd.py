"""Diagnóstico de la conexión Django <-> PostgreSQL. SOLO LEE: no modifica nada.

Responde a la pregunta "¿Django no ve mis datos porque la inserción está mal o porque la lectura está mal?"
Nunca imprime contraseñas, hashes ni datos personales: solo conteos y nombres de tablas.
"""

from django.apps import apps
from django.core.management.base import BaseCommand
from django.db import connection
from django.db.migrations.executor import MigrationExecutor

from core.hashes import normalizar_hashes
from core.models import Usuario

ROLES_VALIDOS = {'administrador', 'asistente', 'donante'}


class Command(BaseCommand):
    help = 'Diagnostica por qué Django no ve (o no puede guardar) datos en PostgreSQL. No modifica nada.'

    # ── utilidades de salida ──
    def titulo(self, texto):
        self.stdout.write('\n' + self.style.MIGRATE_HEADING(f'== {texto} =='))

    def ok(self, texto):
        self.stdout.write(self.style.SUCCESS(f'  ✔ {texto}'))

    def mal(self, texto):
        self.hallazgos.append(texto)
        self.stdout.write(self.style.ERROR(f'  ✘ {texto}'))

    def aviso(self, texto):
        self.stdout.write(self.style.WARNING(f'  ! {texto}'))

    def info(self, texto):
        self.stdout.write(f'    {texto}')

    def consulta(self, sql, params=None):
        with connection.cursor() as cur:
            cur.execute(sql, params)
            return cur.fetchall()

    def handle(self, *args, **opciones):
        self.hallazgos = []
        self.sin_datos = False
        if connection.vendor != 'postgresql':
            self.stderr.write(f'Este diagnóstico es para PostgreSQL; el motor actual es {connection.vendor}.')
            return
        if not self.conexion():
            return
        self.migraciones()
        self.tablas_de_django()
        self.tablas_ajenas()
        self.secuencias()
        self.transacciones_abiertas()
        self.usuarios()
        self.resumen()

    # ── 1. a qué base se conecta REALMENTE Django ──
    def conexion(self):
        self.titulo('1. Conexión (lo que Django usa de verdad)')
        c = connection.settings_dict
        self.info(f'Según .env/settings: base="{c["NAME"]}" usuario="{c["USER"]}" host="{c["HOST"]}" puerto="{c["PORT"]}"')
        try:
            connection.ensure_connection()
        except Exception as e:
            self.mal(f'Django NO puede conectarse: {e}'.strip())
            self.info('Revisa DB_NAME / DB_USER / DB_PASSWORD / DB_HOST / DB_PORT en el archivo .env,')
            self.info('que el servidor esté encendido y que la base exista (psql -l).')
            return False
        base, usuario, ip, puerto, esquema, ruta, version = self.consulta(
            "select current_database(), current_user, coalesce(inet_server_addr()::text, 'socket local'), "
            "inet_server_port(), coalesce(current_schema(), '(ninguno)'), current_setting('search_path'), "
            "split_part(version(), ',', 1)")[0]
        self.ok(f'Conectado a la base "{base}" como "{usuario}" en {ip}:{puerto} ({version})')
        self.info(f'Esquema actual: {esquema}   search_path: {ruta}')
        self.info('>> Verifica que ESTA base, este puerto y este servidor son los MISMOS donde insertaste los datos.')
        self.info('   (Un error común: tener dos PostgreSQL, p. ej. local en 5432 y Docker en 5433.)')
        return True

    # ── 2. migraciones ──
    def migraciones(self):
        self.titulo('2. Migraciones')
        ejecutor = MigrationExecutor(connection)
        pendientes = ejecutor.migration_plan(ejecutor.loader.graph.leaf_nodes())
        if pendientes:
            self.mal(f'Hay {len(pendientes)} migración(es) sin aplicar: ' +
                     ', '.join(f'{m.app_label}.{m.name}' for m, _ in pendientes))
            self.info('Solución: python manage.py migrate')
        else:
            self.ok('Todas las migraciones están aplicadas.')

    # ── 3. las tablas que Django espera ──
    def tablas_de_django(self):
        self.titulo('3. Tablas que Django espera y cuántas filas ve')
        existentes = set(connection.introspection.table_names())
        self.tablas_esperadas = []
        for modelo in apps.get_app_config('core').get_models(include_auto_created=True):
            tabla = modelo._meta.db_table
            self.tablas_esperadas.append(tabla)
            if tabla not in existentes:
                self.mal(f'Falta la tabla "{tabla}" (modelo {modelo.__name__}) en el esquema actual.')
                continue
            filas = modelo._default_manager.count()
            (sql,) = self.consulta(f'select count(*) from {connection.ops.quote_name(tabla)}')[0]
            if filas != sql:
                self.mal(f'{tabla}: el ORM cuenta {filas} pero SQL cuenta {sql}')
            else:
                (self.ok if filas else self.aviso)(f'{tabla}: {filas} fila(s)' + ('' if filas else '  <- VACÍA'))

    # ── 4. tablas con datos que Django NO está leyendo ──
    def tablas_ajenas(self):
        self.titulo('4. Otras tablas en la base (posibles datos en el lugar equivocado)')
        filas = self.consulta(
            "select table_schema, table_name from information_schema.tables "
            "where table_type = 'BASE TABLE' and table_schema not in ('pg_catalog', 'information_schema') "
            "order by 1, 2")
        propias = set(self.tablas_esperadas)
        (actual,) = self.consulta('select current_schema()')[0]
        raras = []
        for esquema, tabla in filas:
            # Lo normal: las tablas de Django y de sus apps (django_*, auth_*) en el esquema actual.
            # Todo lo demás (otro nombre u otro esquema, incluso con el MISMO nombre) es sospechoso.
            if esquema == actual and (tabla in propias or tabla.startswith(('django_', 'auth_'))):
                continue
            raras.append((esquema, tabla))
        if not raras:
            self.ok('No hay tablas ajenas: todo vive en las tablas de Django.')
            return
        for esquema, tabla in raras:
            nombre = f'{connection.ops.quote_name(esquema)}.{connection.ops.quote_name(tabla)}'
            (n,) = self.consulta(f'select count(*) from {nombre}')[0]
            self.aviso(f'{esquema}.{tabla}: {n} fila(s)' + ('  <- tiene datos que Django NO lee' if n else ''))
            if n:
                self.hallazgos.append(f'La tabla {esquema}.{tabla} tiene {n} fila(s) y Django no la usa')
        self.info('Django solo lee las tablas del paso 3 (core_usuario, core_donacion...). Si tus datos están en')
        self.info('otras tablas (usuario, donacion...) o en otro esquema, hay que insertarlos en las de Django')
        self.info('o importarlos con un script; NO basta con que existan en la base.')

    # ── 5. secuencias de los id ──
    def secuencias(self):
        self.titulo('5. Secuencias de los id (afecta al GUARDAR desde Django, no al leer)')
        desfasadas = []
        for tabla in self.tablas_esperadas:
            if tabla not in connection.introspection.table_names():
                continue
            nombre = connection.ops.quote_name(tabla)
            (seq,) = self.consulta('select pg_get_serial_sequence(%s, %s)', [nombre, 'id'])[0]
            if not seq:
                continue
            (maximo,) = self.consulta(f'select coalesce(max(id), 0) from {nombre}')[0]
            ultimo, llamada = self.consulta(f'select last_value, is_called from {seq}')[0]
            siguiente = ultimo + 1 if llamada else ultimo
            if maximo >= siguiente:
                desfasadas.append(tabla)
                self.mal(f'{tabla}: el mayor id es {maximo} pero la secuencia dará el {siguiente} '
                         f'-> el próximo INSERT desde Django fallará con "duplicate key"')
        if desfasadas:
            self.info('Solución (imprime el SQL de reparación y lo ejecuta):')
            self.info('  python manage.py sqlsequencereset core | psql -h HOST -p PUERTO -U USUARIO NOMBRE_BD')
        else:
            self.ok('Todas las secuencias están al día.')

    # ── 6. inserciones sin confirmar ──
    def transacciones_abiertas(self):
        self.titulo('6. Transacciones abiertas sin confirmar (COMMIT)')
        try:
            abiertas = self.consulta(
                "select coalesce(application_name, ''), coalesce(usename, ''), "
                "extract(epoch from now() - xact_start)::int from pg_stat_activity "
                "where datname = current_database() and pid <> pg_backend_pid() "
                "and state in ('idle in transaction', 'idle in transaction (aborted)')")
        except Exception as e:
            self.aviso(f'No pude consultar pg_stat_activity (¿permisos?): {str(e).splitlines()[0]}')
            return
        if not abiertas:
            self.ok('No hay transacciones colgadas.')
            return
        for app, usuario, segundos in abiertas:
            self.mal(f'Hay una sesión ("{app or "sin nombre"}", usuario {usuario}) con una transacción abierta '
                     f'hace {segundos} s: lo que insertó ahí NO es visible para Django hasta que haga COMMIT')
        self.info('Causa típica: psql con BEGIN sin COMMIT, o DBeaver/pgAdmin/DataGrip con auto-commit desactivado.')

    # ── 7. los usuarios: ¿Django los ve y podrían iniciar sesión? ──
    def usuarios(self):
        self.titulo('7. Usuarios (lo que el login y los paneles necesitan)')
        if 'core_usuario' not in connection.introspection.table_names():
            return
        total = Usuario.objects.count()
        if not total:
            self.aviso('No hay ningún usuario.')
            self.sin_datos = True
            return
        self.ok(f'{total} usuario(s) visibles para el ORM.')
        por_rol = {r: n for r, n in self.consulta('select rol, count(*) from core_usuario group by rol')}
        self.info('Por rol: ' + ', '.join(f'{r}={n}' for r, n in sorted(por_rol.items())))
        invalidos = sum(n for r, n in por_rol.items() if r not in ROLES_VALIDOS)
        if invalidos:
            self.mal(f'{invalidos} usuario(s) con un rol que Django no entiende (valores: '
                     f'{sorted(r for r in por_rol if r not in ROLES_VALIDOS)}). Los válidos son: {sorted(ROLES_VALIDOS)} '
                     f'(en minúscula, sin espacios): esos usuarios no entrarán a ningún panel.')
        por_estado = {e: n for e, n in self.consulta('select estado, count(*) from core_usuario group by estado')}
        self.info('Por estado: ' + ', '.join(f'{e}={n}' for e, n in sorted(por_estado.items())))
        otros = sorted(e for e in por_estado if e not in ('activo', 'inactivo'))
        if otros:
            self.mal(f'Estados desconocidos {otros}: solo "activo" puede iniciar sesión.')
        crudos = normalizar_hashes(Usuario, dry_run=True)
        if crudos['convertidos']:
            self.mal(f'{crudos["convertidos"]} usuario(s) con contraseña de Laravel ($2y$...) sin convertir: '
                     f'no podrán iniciar sesión. Solución: python manage.py normalizar_hashes_laravel')
        if crudos['no_reconocidos']:
            self.mal(f'{len(crudos["no_reconocidos"])} usuario(s) con contraseña en un formato desconocido '
                     f'(ids {crudos["no_reconocidos"][:10]}): hay que restablecérsela.')

    # ── veredicto ──
    def resumen(self):
        self.titulo('Resumen')
        if not self.hallazgos and self.sin_datos:
            self.aviso('Django funciona bien, pero la base está VACÍA: no hay nada que leer.')
            self.info('Si ya insertaste datos, probablemente fue en OTRA base, otro puerto u otro servidor:')
            self.info('compara lo del paso 1 con el sitio donde insertaste (en psql: SELECT current_database(),')
            self.info('inet_server_port();). También puede que sea una transacción sin COMMIT (paso 6).')
            return
        if not self.hallazgos:
            self.ok('No encontré problemas: la conexión, las tablas y los usuarios están bien.')
            self.info('Si aun así Django "no ve" algo, dime qué pantalla o consulta concreta y qué error muestra.')
            return
        self.stdout.write(self.style.ERROR(f'  Se encontraron {len(self.hallazgos)} problema(s):'))
        for h in self.hallazgos:
            self.stdout.write(f'   - {h}')
