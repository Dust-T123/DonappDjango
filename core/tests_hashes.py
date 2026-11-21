import importlib
from datetime import date, timedelta
from io import StringIO

import bcrypt
from django.apps import apps
from django.contrib.auth.hashers import PBKDF2PasswordHasher, check_password
from django.core.management import call_command
from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings
from django.urls import reverse

from .forms import DonappPasswordResetForm
from .hashes import a_formato_django, normalizar_hashes
from .models import Usuario
from .tests_usuario import crear_usuario



class PBKDF2Rapido(PBKDF2PasswordHasher):
    """Igual que el PBKDF2 del proyecto (mismo nombre de algoritmo) pero con pocas iteraciones,
    para que los tests no tarden decenas de segundos."""
    iterations = 1000


# Los hashers del proyecto, en su mismo orden: el primero es el preferido y los demás solo leen.
_proyecto = importlib.import_module('config.settings').PASSWORD_HASHERS
HASHERS_REALES = ['core.tests_hashes.PBKDF2Rapido'] + _proyecto[1:]
assert _proyecto[0].endswith('PBKDF2PasswordHasher')
CLAVE = 'Clave123*'


def hash_php(clave=CLAVE, prefijo='$2y$', coste=4):
    """Un hash como lo guarda Laravel/PHP: bcrypt con etiqueta $2y$ (aquí coste 4 por velocidad)."""
    return prefijo + bcrypt.hashpw(clave.encode(), bcrypt.gensalt(rounds=coste)).decode()[4:]


def con_hash(usuario, almacenado):
    """Fija la contraseña tal cual (como llegaría de un volcado de Laravel), saltando save()."""
    Usuario.objects.filter(pk=usuario.pk).update(password=almacenado)
    usuario.refresh_from_db()
    return usuario


class ConversionTests(TestCase):
    def test_conversion_de_formato(self):
        h = hash_php(prefijo='$2y$', coste=10)
        self.assertEqual(a_formato_django(h), 'bcrypt$$2b$10$' + h[7:])
        for etiqueta in ('$2a$', '$2b$', '$2y$'):
            self.assertTrue(a_formato_django(hash_php(prefijo=etiqueta)).startswith('bcrypt$$2b$04$'))

    def test_lo_que_no_es_bcrypto_crudo_no_se_toca(self):
        for valor in (None, '', 'texto', 'pbkdf2_sha256$1$a$b', 'bcrypt$$2b$04$' + 'a' * 53,
                      '$2y$10$corto', '$2y$10$' + 'a' * 60, '$2x$04$' + 'a' * 53, '$1$abc$def'):
            self.assertIsNone(a_formato_django(valor), valor)

    @override_settings(PASSWORD_HASHERS=HASHERS_REALES)
    def test_hash_generado_por_php_de_verdad(self):
        """Vector oficial de la documentación de password_hash() de PHP: $2y$, coste 7."""
        php = '$2y$07$BCryptRequires22Chrcte/VlQH0piJtjXl.0t1XkA8pw9dMXTpOq'
        self.assertTrue(check_password('rasmuslerdorf', a_formato_django(php)))
        self.assertFalse(check_password('rasmuslerdorg', a_formato_django(php)))

    @override_settings(PASSWORD_HASHERS=HASHERS_REALES)
    def test_el_hash_crudo_no_sirve_en_django_y_el_convertido_si(self):
        crudo = hash_php()
        self.assertFalse(check_password(CLAVE, crudo), 'Django no reconoce $2y$ crudo: nadie podría entrar')
        convertido = a_formato_django(crudo)
        self.assertTrue(check_password(CLAVE, convertido))
        self.assertFalse(check_password('otra-clave', convertido))
        self.assertFalse(check_password('', convertido))


@override_settings(PASSWORD_HASHERS=HASHERS_REALES)
class NormalizarHashesTests(TestCase):
    def setUp(self):
        self.y = con_hash(crear_usuario('y@x.co'), hash_php(prefijo='$2y$'))
        self.a = con_hash(crear_usuario('a@x.co'), hash_php(prefijo='$2a$'))
        self.django = crear_usuario('d@x.co')                       # ya en formato Django
        self.inutil = con_hash(crear_usuario('i@x.co'), '!inutilizable')
        self.raro = con_hash(crear_usuario('r@x.co'), 'texto-plano-sospechoso')
        self.menor = con_hash(crear_usuario('menor@x.co'), hash_php())
        Usuario.objects.filter(pk=self.menor.pk).update(fecha_nacimiento=date.today() - timedelta(days=365 * 10))

    def test_resultado_y_estado_final(self):
        r = normalizar_hashes(Usuario)
        self.assertEqual(r['convertidos'], 3)
        self.assertEqual(r['sin_cambios'], 2)
        self.assertEqual(r['no_reconocidos'], [self.raro.id])
        for u in (self.y, self.a, self.menor):
            u.refresh_from_db()
            self.assertTrue(u.password.startswith('bcrypt$$2b$04$'))
            self.assertTrue(u.check_password(CLAVE))
        self.raro.refresh_from_db(); self.assertEqual(self.raro.password, 'texto-plano-sospechoso')
        self.inutil.refresh_from_db(); self.assertEqual(self.inutil.password, '!inutilizable')

    def test_es_idempotente(self):
        normalizar_hashes(Usuario)
        antes = list(Usuario.objects.order_by('id').values_list('password', flat=True))
        r = normalizar_hashes(Usuario)
        self.assertEqual(r['convertidos'], 0)
        self.assertEqual(antes, list(Usuario.objects.order_by('id').values_list('password', flat=True)))

    def test_dry_run_no_modifica_nada(self):
        antes = list(Usuario.objects.order_by('id').values_list('password', flat=True))
        r = normalizar_hashes(Usuario, dry_run=True)
        self.assertEqual(r['convertidos'], 3)
        self.assertEqual(antes, list(Usuario.objects.order_by('id').values_list('password', flat=True)))

    def test_funciona_en_lotes(self):
        for i in range(7):
            con_hash(crear_usuario(f'l{i}@x.co'), hash_php())
        r = normalizar_hashes(Usuario, lote=3)
        self.assertEqual(r['convertidos'], 10)
        self.assertFalse(Usuario.objects.filter(password__startswith='$2').exists())

    def test_comando(self):
        salida, error = StringIO(), StringIO()
        call_command('normalizar_hashes_laravel', '--dry-run', stdout=salida, stderr=error)
        self.assertTrue('Se convertirían: 3' in salida.getvalue() and 'no se modificó' in salida.getvalue())
        self.assertTrue(str(self.raro.id) in error.getvalue(), 'avisa del usuario con formato desconocido')
        self.assertTrue(Usuario.objects.filter(password__startswith='$2y$').exists())
        salida = StringIO(); call_command('normalizar_hashes_laravel', stdout=salida, stderr=StringIO())
        self.assertTrue('Convertidos: 3' in salida.getvalue())
        self.assertFalse(Usuario.objects.filter(password__startswith='$2').exists())
        self.assertFalse('$2' in salida.getvalue() + error.getvalue(), 'la salida nunca muestra hashes')

    def test_la_migracion_de_datos_hace_lo_mismo(self):
        migracion = importlib.import_module('core.migrations.0003_normalizar_hashes_laravel')
        migracion.convertir(apps, None)
        self.assertFalse(Usuario.objects.filter(password__startswith='$2').exists())


@override_settings(PASSWORD_HASHERS=HASHERS_REALES)
class LoginConContrasenasDeLaravelTests(TestCase):
    def setUp(self):
        self.ana = con_hash(crear_usuario('ana@x.co'), hash_php())

    def entrar(self, clave=CLAVE):
        return self.client.post(reverse('login'), {'email': 'ana@x.co', 'contrasena': clave})

    def test_sin_normalizar_nadie_puede_entrar(self):
        """Documenta el problema que resuelve el comando: con la contraseña correcta, el login falla."""
        r = self.entrar()
        self.assertEqual(r.status_code, 200)
        self.assertTrue('Contraseña incorrecta' in r.content.decode())

    def test_tras_normalizar_entra_y_la_contrasena_se_actualiza_a_pbkdf2(self):
        normalizar_hashes(Usuario)
        r = self.entrar()
        self.assertRedirects(r, reverse('login_exitoso'), fetch_redirect_response=False)
        self.ana.refresh_from_db()
        self.assertTrue(self.ana.password.startswith('pbkdf2_sha256$'), 'se re-hashea sola en el primer login')
        self.assertTrue(self.ana.check_password(CLAVE), 'y la contraseña sigue siendo la misma')

    def test_clave_incorrecta_no_entra_ni_cambia_el_hash(self):
        normalizar_hashes(Usuario)
        self.ana.refresh_from_db(); antes = self.ana.password
        r = self.entrar('equivocada')
        self.assertTrue('Contraseña incorrecta' in r.content.decode())
        self.ana.refresh_from_db(); self.assertEqual(self.ana.password, antes)

    def test_la_recuperacion_de_contrasena_funciona_tras_normalizar(self):
        normalizar_hashes(Usuario)
        self.assertEqual([u.email for u in DonappPasswordResetForm().get_users('ana@x.co')], ['ana@x.co'])

    def test_cuenta_inactiva_sigue_bloqueada(self):
        normalizar_hashes(Usuario)
        Usuario.objects.filter(pk=self.ana.pk).update(estado='inactivo')
        self.assertTrue('restringido' in self.entrar().content.decode())

    def test_dato_antiguo_que_ya_no_cumple_las_reglas_no_impide_entrar(self):
        """Antes: el re-hash llamaba a save() -> clean() -> ValidationError -> 500 en el login."""
        Usuario.objects.filter(pk=self.ana.pk).update(fecha_nacimiento=date.today() - timedelta(days=365 * 10))
        normalizar_hashes(Usuario)
        self.assertRedirects(self.entrar(), reverse('login_exitoso'), fetch_redirect_response=False)


class SaveParcialTests(TestCase):
    def test_guardado_parcial_no_valida_campos_ajenos_pero_el_completo_si(self):
        u = crear_usuario('v@x.co')
        Usuario.objects.filter(pk=u.pk).update(fecha_nacimiento=date.today() - timedelta(days=365 * 10))
        u.refresh_from_db()
        u.estado = 'inactivo'
        u.save(update_fields=['estado'])                     # no toca los campos validados: pasa
        with self.assertRaises(ValidationError):
            u.save()                                          # guardado completo: sí valida
        with self.assertRaises(ValidationError):
            u.save(update_fields=['fecha_nacimiento', 'estado'])   # toca un campo validado: valida
