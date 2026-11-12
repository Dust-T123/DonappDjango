from datetime import date, timedelta

from django.core import mail
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from .models import Donacion, Evento, Solicitud, Usuario


def crear_usuario(email='ana@correo.com', rol='donante', estado='activo', clave='Clave-Segura-9', **extra):
    datos = dict(
        nombre='Ana', apellido='Gómez', tipo_documento='CC',
        num_documento=email.split('@')[0] + '12345', fecha_nacimiento=date(1990, 1, 1),
        direccion='Calle 1 # 2-3', telefono='3001234567', rol=rol, estado=estado,
    )
    datos.update(extra)
    return Usuario.objects.create_user(email=email, password=clave, **datos)


class ModelosTests(TestCase):
    def test_edad_minima_14(self):
        menor = date.today() - timedelta(days=365 * 10)
        with self.assertRaises(ValidationError):
            crear_usuario(email='nino@correo.com', fecha_nacimiento=menor)

    def test_solo_donante_tiene_necesidad(self):
        with self.assertRaises(ValidationError):
            crear_usuario(email='adm@correo.com', rol='administrador', necesidad='algo')

    def test_solo_donante_crea_solicitud(self):
        asistente = crear_usuario(email='asis@correo.com', rol='asistente')
        with self.assertRaises(ValidationError):
            Solicitud.objects.create(descripcion='x', solicitante=asistente)


class LoginTests(TestCase):
    def test_login_correcto_redirige_a_pantalla_de_exito(self):
        crear_usuario()
        r = self.client.post(reverse('login'), {'email': 'ANA@correo.com', 'contrasena': 'Clave-Segura-9'})
        self.assertRedirects(r, reverse('login_exitoso'))

    def test_contrasena_incorrecta(self):
        crear_usuario()
        r = self.client.post(reverse('login'), {'email': 'ana@correo.com', 'contrasena': 'mala'})
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'Contraseña incorrecta')

    def test_usuario_inactivo(self):
        crear_usuario(estado='inactivo')
        r = self.client.post(reverse('login'), {'email': 'ana@correo.com', 'contrasena': 'Clave-Segura-9'})
        self.assertContains(r, 'restringido')

    def test_correo_inexistente(self):
        r = self.client.post(reverse('login'), {'email': 'no@correo.com', 'contrasena': 'x'})
        self.assertContains(r, 'No encontramos una cuenta')

    def test_logout_solo_post(self):
        crear_usuario()
        self.client.login(email='ana@correo.com', password='Clave-Segura-9')
        self.assertEqual(self.client.get(reverse('logout')).status_code, 405)
        self.assertRedirects(self.client.post(reverse('logout')), reverse('login'))


class RolesTests(TestCase):
    def test_sin_sesion_va_al_login(self):
        self.assertRedirects(self.client.get(reverse('dashboard_usuario')), reverse('login'))

    def test_rol_equivocado_vuelve_a_su_panel(self):
        crear_usuario(email='asis@correo.com', rol='asistente')
        self.client.login(email='asis@correo.com', password='Clave-Segura-9')
        r = self.client.get(reverse('dashboard_administrador'))
        self.assertRedirects(r, reverse('dashboard_asistente'), fetch_redirect_response=False)

    def test_cuenta_desactivada_pierde_la_sesion(self):
        u = crear_usuario()
        self.client.login(email='ana@correo.com', password='Clave-Segura-9')
        self.assertEqual(self.client.get(reverse('dashboard_usuario')).status_code, 200)
        u.estado = 'inactivo'
        u.save()
        self.assertRedirects(self.client.get(reverse('dashboard_usuario')), reverse('login'))


class RegistroTests(TestCase):
    datos = {
        'nombre': 'Luis', 'apellido': 'Pérez', 'tipoDocumento': 'CC', 'numDocumento': 'ABC1234',
        'fechaNacimiento': '1990-05-10', 'direccion': 'Calle 5 # 6-7', 'email': 'luis@correo.com',
        'telefono': '3001112233', 'password': 'Clave-Segura-9', 'password_confirmation': 'Clave-Segura-9',
        'necesidad': '', 'aceptaTerminos': 'on',
    }

    def test_registro_valido_crea_donante(self):
        self.assertRedirects(self.client.post(reverse('registro'), self.datos), reverse('login'))
        u = Usuario.objects.get(email='luis@correo.com')
        self.assertEqual((u.rol, u.estado), ('donante', 'activo'))
        self.assertTrue(u.check_password('Clave-Segura-9'))

    def test_menor_de_14_rechazado(self):
        d = dict(self.datos, fechaNacimiento=str(date.today() - timedelta(days=365 * 10)))
        self.client.post(reverse('registro'), d)
        self.assertFalse(Usuario.objects.filter(email='luis@correo.com').exists())

    def test_contrasenas_distintas(self):
        d = dict(self.datos, password_confirmation='otra')
        self.client.post(reverse('registro'), d)
        self.assertFalse(Usuario.objects.exists())

    def test_correo_duplicado(self):
        crear_usuario(email='luis@correo.com')
        self.client.post(reverse('registro'), self.datos)
        self.assertEqual(Usuario.objects.count(), 1)


class RecuperarTests(TestCase):
    def test_envia_correo_a_cuenta_activa(self):
        crear_usuario()
        r = self.client.post(reverse('recuperar'), {'email': 'ana@correo.com'})
        self.assertRedirects(r, reverse('recuperar'))
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('/restablecer/', mail.outbox[0].body)

    def test_no_envia_a_inactiva_ni_inexistente(self):
        crear_usuario(estado='inactivo')
        self.client.post(reverse('recuperar'), {'email': 'ana@correo.com'})
        self.client.post(reverse('recuperar'), {'email': 'nadie@correo.com'})
        self.assertEqual(len(mail.outbox), 0)


class ApiTests(TestCase):
    def setUp(self):
        Evento.objects.create(nombre='Activo', estado='publicado')
        Evento.objects.create(nombre='Borrador', estado='borrador')

    def test_estadisticas(self):
        crear_usuario()
        Donacion.objects.create(descripcion='x', stock=1)
        d = self.client.get('/api/estadisticas').json()
        self.assertTrue(d['success'])
        self.assertEqual(d['data']['total_donantes'], 1)
        self.assertEqual(d['data']['eventos_activos'], 1)

    def test_eventos_solo_activos(self):
        d = self.client.get('/api/eventos').json()
        self.assertEqual(d['total'], 1)
        self.assertEqual(d['data'][0]['nombre'], 'Activo')

    def test_evento_inactivo_404(self):
        borrador = Evento.objects.get(nombre='Borrador')
        self.assertEqual(self.client.get(f'/api/eventos/{borrador.pk}').status_code, 404)

    def test_index_carga(self):
        self.assertEqual(self.client.get('/').status_code, 200)
