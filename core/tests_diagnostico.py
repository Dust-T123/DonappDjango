from datetime import date
from io import StringIO
from unittest import skipUnless

from django.core.management import call_command
from django.db import IntegrityError, connection, transaction
from django.test import TestCase
from django.urls import reverse

from .models import Categoria, Usuario
from .tests_usuario import crear_usuario


class RolInvalidoTests(TestCase):
    """Un rol que no existe (cargado a mano en la BD) no debe provocar un bucle de redirecciones."""

    def setUp(self):
        self.u = crear_usuario('mal@x.co')
        Usuario.objects.filter(pk=self.u.pk).update(rol='Donante')      # como una inserción directa con mayúscula

    def test_no_puede_iniciar_sesion_y_se_le_explica_por_que(self):
        r = self.client.post(reverse('login'), {'email': 'mal@x.co', 'contrasena': 'Clave123*'})
        self.assertEqual(r.status_code, 200)
        self.assertTrue('rol no válido' in r.content.decode())
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_con_la_sesion_ya_abierta_se_cierra_en_vez_de_rebotar_sin_fin(self):
        self.client.force_login(self.u)
        for url in ('dashboard_usuario', 'dashboard_asistente', 'dashboard_administrador'):
            self.client.force_login(self.u)
            r = self.client.get(reverse(url), follow=True)
            self.assertEqual(r.redirect_chain[-1][0], reverse('login'), url)       # termina en el login, sin bucle
            self.assertTrue('rol no válido' in r.content.decode(), url)
            self.assertNotIn('_auth_user_id', self.client.session, url)

    def test_el_rol_correcto_sigue_funcionando(self):
        Usuario.objects.filter(pk=self.u.pk).update(rol='donante')
        r = self.client.post(reverse('login'), {'email': 'mal@x.co', 'contrasena': 'Clave123*'})
        self.assertRedirects(r, reverse('login_exitoso'), fetch_redirect_response=False)


@skipUnless(connection.vendor == 'postgresql', 'El diagnóstico es solo para PostgreSQL')
class DiagnosticarBdTests(TestCase):
    def correr(self):
        salida = StringIO()
        call_command('diagnosticar_bd', stdout=salida, stderr=StringIO())
        return salida.getvalue()

    def test_base_vacia_se_dice_claramente(self):
        texto = self.correr()
        self.assertTrue('Todas las migraciones están aplicadas' in texto)
        self.assertTrue('VACÍA' in texto)
        self.assertTrue('OTRA base, otro puerto' in texto, 'orienta cuando la base no tiene datos')

    def test_detecta_datos_en_tablas_que_django_no_lee(self):
        with connection.cursor() as c:
            c.execute('create table usuario (id serial, nombre text)')
            c.execute("insert into usuario (nombre) values ('Ana'), ('Beto')")
        texto = self.correr()
        self.assertTrue('public.usuario: 2 fila(s)' in texto and 'Django NO lee' in texto)

    def test_detecta_secuencias_desfasadas_y_el_guardado_realmente_falla(self):
        # Se inserta con un id EXPLÍCITO igual al que la secuencia entregará después (como haría una
        # carga directa por SQL). No depende de qué otras pruebas hayan avanzado la secuencia.
        with connection.cursor() as c:
            c.execute("select last_value, is_called from core_categoria_id_seq")
            ultimo, llamada = c.fetchone()
            siguiente = ultimo + 1 if llamada else ultimo
            c.execute("insert into core_categoria (id, nombre) values (%s, 'Ropa')", [siguiente])
        self.assertTrue(f'core_categoria: el mayor id es {siguiente}' in self.correr())
        with self.assertRaises(IntegrityError):                              # el síntoma real
            with transaction.atomic():
                Categoria.objects.create(nombre='Nueva')

    def test_detecta_usuarios_inutilizables(self):
        base = dict(apellido='X', tipo_documento='CC', fecha_nacimiento=date(1990, 1, 1),
                    direccion='Calle 1 # 2', telefono='3001234567')
        Usuario.objects.bulk_create([
            Usuario(nombre='A', num_documento='1001', email='a@x.co', rol='Donante', estado='Activo',
                    password='$2y$10$' + 'a' * 53, **base)])
        texto = self.correr()
        self.assertTrue("rol que Django no entiende" in texto and "'Donante'" in texto)
        self.assertTrue("Estados desconocidos ['Activo']" in texto)
        self.assertTrue('normalizar_hashes_laravel' in texto)

    def test_nunca_imprime_hashes_ni_contrasenas_ni_correos(self):
        crear_usuario('x@x.co')
        with connection.cursor() as c:
            c.execute("update core_usuario set password = %s", ['$2y$10$' + 'Z' * 53])
        original = connection.settings_dict['PASSWORD']
        connection.settings_dict['PASSWORD'] = 'Contrasena-Unica-Inconfundible-123'   # la conexión ya está abierta
        try:
            texto = self.correr()
        finally:
            connection.settings_dict['PASSWORD'] = original
        self.assertFalse('ZZZZ' in texto, 'no imprime hashes')
        self.assertFalse('x@x.co' in texto, 'no imprime correos')
        self.assertFalse('Inconfundible' in texto, 'no imprime la contraseña de la base de datos')
