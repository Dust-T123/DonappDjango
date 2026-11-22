"""Pruebas del parche de correcciones: documento alfanumérico, validaciones comunes,
historial con cancelados, textos sin la palabra prohibida y errores ocultos."""

import re
import tempfile
from datetime import date
from types import SimpleNamespace

from django.contrib.messages import get_messages
from django.test import TestCase, override_settings
from django.urls import reverse

from .forms import normalizar_documento, validar_numero_documento, validar_valor_correccion
from .models import Categoria, CorreccionDatos, Donacion, DonacionUsuario, Evento, Solicitud, Usuario
from .tests_administrador import archivo
from .tests_usuario import crear_usuario
from .utils import fecha_hace_anios

# La palabra que no debe aparecer en el sitio, armada para que ni este archivo la contenga.
PALABRA_PROHIBIDA = 'clien' + 'te'
HOY = date.today()


def datos_registro(**extra):
    datos = {
        'nombre': 'Luis', 'apellido': 'Pérez', 'tipoDocumento': 'Pasaporte', 'numDocumento': 'ab12345',
        'fechaNacimiento': '1990-05-10', 'direccion': 'Calle 5 # 6-7', 'email': 'luis@correo.com',
        'telefono': '3001112233', 'password': 'Clave-Segura-9', 'password_confirmation': 'Clave-Segura-9',
        'necesidad': '', 'aceptaTerminos': 'on',
    }
    datos.update(extra)
    return datos


class DocumentoPorTipoTests(TestCase):
    def test_pasaporte_acepta_letras_y_lo_guarda_en_mayusculas(self):
        self.client.post(reverse('registro'), datos_registro())
        self.assertEqual(Usuario.objects.get(email='luis@correo.com').num_documento, 'AB12345')

    def test_registro_rechaza_documentos_invalidos(self):
        for malo in ('AB 123', 'AB-123', 'A1', 'ABCDEFGHIJ1234567', 'ñandú123'):
            self.client.post(reverse('registro'), datos_registro(numDocumento=malo))
        self.assertFalse(Usuario.objects.exists())

    def test_solo_el_pasaporte_admite_letras(self):
        for tipo in ('CC', 'TI', 'CE', 'TE', 'PPT'):
            self.client.post(reverse('registro'), datos_registro(tipoDocumento=tipo, numDocumento='AB12345'))
            self.client.post(reverse('registro'), datos_registro(tipoDocumento=tipo, numDocumento='12 345'))
        self.assertFalse(Usuario.objects.exists())
        for i, tipo in enumerate(('CC', 'TI', 'CE', 'TE', 'PPT')):
            self.client.post(reverse('registro'), datos_registro(
                tipoDocumento=tipo, numDocumento=f'10020030{i}', email=f'u{i}@correo.com'))
        self.assertEqual(Usuario.objects.count(), 5)

    def test_duplicado_sin_importar_mayusculas(self):
        self.client.post(reverse('registro'), datos_registro())
        self.client.post(reverse('registro'), datos_registro(numDocumento='AB12345', email='otro@correo.com'))
        self.client.post(reverse('registro'), datos_registro(numDocumento='Ab12345', email='otro2@correo.com'))
        self.assertEqual(Usuario.objects.count(), 1)

    def test_registro_valida_tipo_de_caracteres_y_longitudes(self):
        for extra in ({'nombre': 'Luis123'}, {'apellido': 'Pé4rez'}, {'telefono': '30011122AB'},
                      {'telefono': '300111223'}, {'telefono': '30011122334'},
                      {'password': 'x' * 31, 'password_confirmation': 'x' * 31}):
            self.client.post(reverse('registro'), datos_registro(**extra))
        self.assertFalse(Usuario.objects.exists())

    def test_pasaporte_esta_en_el_registro(self):
        self.assertContains(self.client.get(reverse('registro')), 'value="Pasaporte"')


@override_settings(MEDIA_ROOT=tempfile.mkdtemp(), PRIVATE_MEDIA_ROOT=tempfile.mkdtemp())
class PersonalTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = crear_usuario('adm@x.co', rol='administrador')
        cls.admin2 = crear_usuario('adm2@x.co', rol='administrador')
        cls.asis = crear_usuario('asis@x.co', rol='asistente')
        cls.ana = crear_usuario('ana@x.co', necesidad='Comida')
        cls.cat = Categoria.objects.create(nombre='Ropa')

    def alta(self, **extra):
        datos = {'nombre': 'Carlos', 'apellido': 'Ruiz', 'tipoDocumento': 'PPT', 'numDocumento': '99887766',
                 'fechaNacimiento': '1985-05-05', 'direccion': 'Calle 5 # 6-7', 'email': 'carlos@x.co',
                 'telefono': '3011112222', 'password': 'Segura987*', 'password_confirmation': 'Segura987*',
                 'prioridad': 'alta', 'necesidad': 'Mercado'}
        datos.update(extra)
        return datos

    def test_asistente_y_administrador_registran_documentos_con_letras(self):
        self.client.force_login(self.asis)
        self.client.post(reverse('asis_donante_crear'), self.alta())
        self.assertEqual(Usuario.objects.get(email='carlos@x.co').num_documento, '99887766')
        self.client.force_login(self.admin)
        self.client.post(reverse('adm_usuario_crear'), self.alta(
            email='dos@x.co', numDocumento='pa123456', tipoDocumento='Pasaporte', rol='donante', estado='activo'))
        self.assertEqual(Usuario.objects.get(email='dos@x.co').num_documento, 'PA123456')

    def test_alta_valida_caracteres_de_nombre_y_documento(self):
        self.client.force_login(self.asis)
        for extra in ({'nombre': 'Carl0s'}, {'apellido': 'R2'}, {'numDocumento': 'AB 12'}, {'numDocumento': 'A-123456'},
                      {'numDocumento': 'AB123456'}):
            self.client.post(reverse('asis_donante_crear'), self.alta(**extra))
        self.assertFalse(Usuario.objects.filter(email='carlos@x.co').exists())

    def test_mensajes_del_asistente_no_dicen_donante(self):
        self.client.force_login(self.asis)
        r = self.client.post(reverse('asis_donante_crear'), self.alta(), follow=True)
        textos = ' '.join(str(m) for m in get_messages(r.wsgi_request))
        self.assertTrue('Donante/solicitante creado' in textos)
        self.assertFalse(PALABRA_PROHIBIDA in textos.lower())
        r = self.client.post(reverse('asis_donante_crear'), self.alta(fechaNacimiento=str(HOY), email='z@x.co',
                                                                      numDocumento='ZZ9999'), follow=True)
        self.assertFalse(PALABRA_PROHIBIDA in ' '.join(str(m) for m in get_messages(r.wsgi_request)).lower())

    def test_paneles_no_muestran_la_palabra_donante(self):
        for quien, nombre in ((self.asis, 'dashboard_asistente'), (self.admin, 'dashboard_administrador'),
                              (self.ana, 'dashboard_usuario')):
            self.client.force_login(quien)
            html = self.client.get(reverse(nombre)).content.decode()
            html = re.sub(r'<(script|style)\b.*?</\1>', ' ', html, flags=re.S | re.I)   # el código no es texto visible
            visible = re.sub(r'<[^>]*>', ' ', html)
            self.assertFalse(PALABRA_PROHIBIDA in visible.lower(), nombre)

    # ── correcciones: el valor propuesto se valida al pedirlo ──
    def pedir(self, campo, valor):
        self.client.force_login(self.admin)
        return self.client.post(reverse('adm_usuario_correccion', args=[self.ana.id]), {
            'campo': campo, 'valorNuevo': valor, 'justificacion': 'Error de digitación',
            'consentimiento': 'on', 'soporte': archivo()})

    def test_correccion_rechaza_valores_invalidos_desde_el_inicio(self):
        for campo, valor in (('numDocumento', 'a b'), ('numDocumento', 'AB'), ('numDocumento', 'A' * 16),
                             ('tipoDocumento', 'XX'), ('fechaNacimiento', 'ayer'),
                             ('nombre', 'Ana123'), ('nombre', 'Al'), ('apellido', 'P'), ('apellido', 'Gómez9')):
            self.pedir(campo, valor)
        self.assertFalse(CorreccionDatos.objects.exists())

    def test_correccion_acepta_documento_con_letras_solo_si_es_pasaporte(self):
        self.pedir('numDocumento', 'ab12345')              # ana es CC: no admite letras
        self.assertFalse(CorreccionDatos.objects.exists())
        Usuario.objects.filter(pk=self.ana.pk).update(tipo_documento='Pasaporte')
        self.ana.refresh_from_db()
        self.pedir('numDocumento', 'ab12345')
        c = CorreccionDatos.objects.get()
        self.assertEqual(c.valor_nuevo, 'ab12345')      # lo propuesto se guarda tal cual
        self.client.force_login(self.admin2)
        self.client.post(reverse('adm_correccion_aprobar', args=[c.id]))
        self.ana.refresh_from_db()
        self.assertEqual(self.ana.num_documento, 'AB12345')     # al aplicarse queda normalizado

    def test_funciones_de_validacion(self):
        self.assertEqual(normalizar_documento('  ab12 '), 'AB12')
        pasaporte, cedula = SimpleNamespace(tipo_documento='Pasaporte'), SimpleNamespace(tipo_documento='CC')
        self.assertEqual(validar_valor_correccion('numDocumento', 'ce99887', pasaporte)[0], 'CE99887')
        self.assertTrue(validar_valor_correccion('numDocumento', 'ce99887', cedula)[1])
        self.assertEqual(validar_valor_correccion('numDocumento', '99887', cedula)[0], '99887')
        self.assertTrue(validar_valor_correccion('numDocumento', 'a-b', pasaporte)[1])
        for tipo in ('CC', 'TI', 'CE', 'TE', 'PPT'):
            self.assertIsNone(validar_numero_documento(tipo, '1234567'))
            self.assertTrue(validar_numero_documento(tipo, '12A4567'))
        self.assertIsNone(validar_numero_documento('Pasaporte', 'AB12345'))
        self.assertEqual(validar_valor_correccion('nombre', '  María   José ')[0], 'María José')
        self.assertTrue(validar_valor_correccion('fechaNacimiento', '2020-13-45')[1])    # no lanza ValueError

    # ── historial: lo cancelado por el donante sigue visible ──
    def test_cancelada_por_el_donante_se_ve_en_historial_y_el_personal_no_la_reabre(self):
        d = Donacion.objects.create(descripcion='Mesa', categoria=self.cat, stock=1)
        DonacionUsuario.objects.create(donante=self.ana, donacion=d)
        s = Solicitud.objects.create(descripcion='Cobijas', solicitante=self.ana, categoria=self.cat)
        self.client.force_login(self.ana)
        self.client.post(reverse('usuario_donacion_cancelar', args=[d.id]))
        self.client.post(reverse('usuario_solicitud_cancelar', args=[s.id]))
        d.refresh_from_db(); s.refresh_from_db()
        self.assertEqual((d.estado, s.estado), ('cancelada', 'cancelada'))
        r = self.client.get(reverse('dashboard_usuario'), {'don_estado': 'cancelada'})
        self.assertEqual([x.descripcion for x in r.context['mis_donaciones']], ['Mesa'])
        # el asistente la ve en el historial del donante...
        self.client.force_login(self.asis)
        datos = self.client.get(reverse('asis_donante_historial', args=[self.ana.id])).json()
        self.assertEqual(datos['donaciones'][0]['estado'], 'cancelada')
        self.assertEqual(datos['solicitudes'][0]['estado'], 'cancelada')
        # ...pero no puede reabrirla
        self.client.post(reverse('asis_donacion_estado', args=[d.id]), {'estado': 'aprobada'})
        self.client.post(reverse('asis_solicitud_estado', args=[s.id]), {'estado': 'aprobada'})
        d.refresh_from_db(); s.refresh_from_db()
        self.assertEqual((d.estado, s.estado), ('cancelada', 'cancelada'))

    # ── errores ocultos ──
    def test_observacion_de_donacion_no_puede_pasar_de_200(self):
        d = Donacion.objects.create(descripcion='Mesa', categoria=self.cat, stock=1)
        DonacionUsuario.objects.create(donante=self.ana, donacion=d)
        self.client.force_login(self.asis)
        r = self.client.post(reverse('asis_donacion_estado', args=[d.id]), {'estado': 'aprobada', 'observacion': 'x' * 201})
        self.assertEqual(r.status_code, 302)               # antes: error 500 (varchar(200))
        d.refresh_from_db(); self.assertEqual(d.estado, 'pendiente')
        self.client.post(reverse('asis_donacion_estado', args=[d.id]), {'estado': 'aprobada', 'observacion': 'x' * 200})
        d.refresh_from_db(); self.assertEqual(d.estado, 'aprobada')

    def test_titulo_de_evento_no_puede_pasar_de_150(self):
        self.client.force_login(self.asis)
        base = {'nombre_evento': 'Jornada', 'fecha_inicio': HOY.isoformat(), 'fecha_fin': HOY.isoformat(),
                'lugar_entrega': 'Sede', 'contenido_pub': 'Detalles de la jornada'}
        r = self.client.post(reverse('asis_evento_crear'), {**base, 'titulo_pub': 'T' * 151})
        self.assertEqual(r.status_code, 302)               # antes: error 500 (varchar(150))
        self.assertFalse(Evento.objects.exists())
        self.client.post(reverse('asis_evento_crear'), {**base, 'titulo_pub': 'T' * 150})
        self.assertEqual(Evento.objects.count(), 1)

    def test_categorias_del_catalogo_con_coma_o_dos_puntos_se_pueden_editar(self):
        cat = Categoria.objects.create(nombre='Periféricos: Mouse, Teclado, Cámaras')
        self.client.force_login(self.asis)
        self.client.post(reverse('asis_categoria_editar', args=[cat.id]),
                         {'nombre_categoria': 'Periféricos: Mouse, Teclado, Cámaras y más'})
        cat.refresh_from_db()
        self.assertEqual(cat.nombre, 'Periféricos: Mouse, Teclado, Cámaras y más')
        self.client.post(reverse('asis_categoria_editar', args=[cat.id]), {'nombre_categoria': 'Con 123 números'})
        cat.refresh_from_db()
        self.assertEqual(cat.nombre, 'Periféricos: Mouse, Teclado, Cámaras y más')

    def test_fecha_hace_anios_no_falla_el_29_de_febrero(self):
        self.assertEqual(fecha_hace_anios(14, date(2028, 2, 29)), date(2014, 2, 28))
        self.assertEqual(fecha_hace_anios(4, date(2028, 2, 29)), date(2024, 2, 29))
        self.assertEqual(fecha_hace_anios(14, date(2026, 11, 21)), date(2012, 11, 21))
