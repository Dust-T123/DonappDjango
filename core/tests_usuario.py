import io
import os
import tempfile
from datetime import date, timedelta

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import (
    Categoria, CorreccionDatos, Donacion, DonacionUsuario, Evento, Solicitud,
    Usuario, VisitaDomiciliaria, VisitaObservacion,
)

def _png():
    from PIL import Image
    buffer = io.BytesIO()
    Image.new('RGB', (2, 2), 'red').save(buffer, 'PNG')
    return buffer.getvalue()


PNG = _png()


def crear_usuario(email, rol='donante', **extra):
    datos = dict(nombre='Ana María', apellido='Pérez', tipo_documento='CC', num_documento=email.split('@')[0],
                 fecha_nacimiento=date(1990, 1, 1), direccion='Calle 1 # 2-3', telefono='3001234567', estado='activo')
    datos.update(extra)
    return Usuario.objects.create_user(email=email, password='Clave123*', rol=rol, **datos)


@override_settings(MEDIA_ROOT=tempfile.mkdtemp(), PRIVATE_MEDIA_ROOT=tempfile.mkdtemp())
class PanelDonanteTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.ana = crear_usuario('ana@x.co')
        cls.otro = crear_usuario('otro@x.co')
        cls.asis = crear_usuario('asis@x.co', rol='asistente')
        cls.admin = crear_usuario('adm@x.co', rol='administrador')
        cls.cat = Categoria.objects.create(nombre='Ropa')

    def setUp(self):
        self.client.force_login(self.ana)

    # ── acceso por rol ──
    def test_redireccion_por_rol(self):
        url = reverse('dashboard_usuario')
        self.client.force_login(self.asis)
        r = self.client.get(url)
        self.assertEqual(r.status_code, 403)
        self.assertContains(r, reverse('dashboard_asistente'), status_code=403)
        self.client.force_login(self.admin)
        r = self.client.get(url)
        self.assertEqual(r.status_code, 403)
        self.assertContains(r, reverse('dashboard_administrador'), status_code=403)
        self.client.logout()
        self.assertRedirects(self.client.get(url), reverse('login'), fetch_redirect_response=False)

    def test_acciones_exigen_post(self):
        self.assertEqual(self.client.get(reverse('usuario_donacion_crear')).status_code, 405)

    def test_dashboard_renderiza_todas_las_pestanas(self):
        for tab in ('inicio', 'donaciones', 'solicitudes', 'visitas', 'eventos', 'perfil', 'invalida'):
            r = self.client.get(reverse('dashboard_usuario'), {'tab': tab})
            self.assertEqual(r.status_code, 200, tab)

    # ── donaciones ──
    def test_crear_editar_cancelar_donacion(self):
        r = self.client.post(reverse('usuario_donacion_crear'), {
            'descripcion': 'Camisas talla M', 'idCategoria': self.cat.id, 'stock': 3,
            'imagen': SimpleUploadedFile('a.png', PNG, content_type='image/png')})
        self.assertEqual(r.status_code, 302)
        d = Donacion.objects.get()
        self.assertEqual((d.estado, d.stock), ('pendiente', 3))
        self.assertTrue(d.imagen)
        self.assertTrue(DonacionUsuario.objects.filter(donante=self.ana, donacion=d).exists())

        html = self.client.get(reverse('dashboard_usuario'), {'tab': 'donaciones'}).content.decode()
        self.assertTrue('Camisas talla M' in html)
        self.assertTrue(d.imagen.url in html)

        self.client.post(reverse('usuario_donacion_editar', args=[d.id]),
                         {'descripcion': 'Camisas talla L', 'idCategoria': self.cat.id, 'stock': 5})
        d.refresh_from_db()
        self.assertEqual((d.descripcion, d.stock), ('Camisas talla L', 5))
        self.assertTrue(d.imagen, 'sin archivo nuevo se conserva la imagen')

        self.client.post(reverse('usuario_donacion_cancelar', args=[d.id]))
        # Cancelar no borra: la donación queda en el historial con estado "cancelada".
        d.refresh_from_db()
        self.assertEqual(d.estado, 'cancelada')
        self.assertTrue(DonacionUsuario.objects.filter(donante=self.ana, donacion=d).exists())
        html = self.client.get(reverse('dashboard_usuario'), {'tab': 'donaciones'}).content.decode()
        self.assertTrue('Camisas talla L' in html)
        # ya cancelada: no se vuelve a cancelar ni a editar
        self.assertEqual(self.client.post(reverse('usuario_donacion_cancelar', args=[d.id])).status_code, 404)

    def test_donacion_invalida_no_se_crea(self):
        for datos in ({'descripcion': 'ab', 'idCategoria': self.cat.id, 'stock': 1},
                      {'descripcion': 'Algo valido', 'idCategoria': 999, 'stock': 1},
                      {'descripcion': 'Algo valido', 'idCategoria': self.cat.id, 'stock': 0},
                      {'descripcion': 'Algo valido', 'idCategoria': self.cat.id, 'stock': 10000}):
            self.client.post(reverse('usuario_donacion_crear'), datos)
        self.assertFalse(Donacion.objects.exists())

    def test_imagen_falsa_rechazada(self):
        self.client.post(reverse('usuario_donacion_crear'), {
            'descripcion': 'Con archivo falso', 'idCategoria': self.cat.id, 'stock': 1,
            'imagen': SimpleUploadedFile('x.png', b'<?php echo 1;', content_type='image/png')})
        self.assertFalse(Donacion.objects.exists())

    def test_no_puede_tocar_donacion_ajena_ni_no_pendiente(self):
        d = Donacion.objects.create(descripcion='De otro', categoria=self.cat)
        DonacionUsuario.objects.create(donante=self.otro, donacion=d)
        for nombre in ('usuario_donacion_editar', 'usuario_donacion_cancelar'):
            r = self.client.post(reverse(nombre, args=[d.id]),
                                 {'descripcion': 'Hackeada!', 'idCategoria': self.cat.id, 'stock': 1})
            self.assertEqual(r.status_code, 404)
        propia = Donacion.objects.create(descripcion='Aprobada ya', categoria=self.cat, estado='aprobada')
        DonacionUsuario.objects.create(donante=self.ana, donacion=propia)
        self.assertEqual(self.client.post(reverse('usuario_donacion_cancelar', args=[propia.id])).status_code, 404)
        self.assertEqual(Donacion.objects.count(), 2)

    def test_filtros_y_stats(self):
        for desc, est in (('Zapatos', 'pendiente'), ('Abrigo', 'aprobada'), ('Mesa', 'aprobada')):
            d = Donacion.objects.create(descripcion=desc, estado=est, categoria=self.cat)
            DonacionUsuario.objects.create(donante=self.ana, donacion=d)
        ajena = Donacion.objects.create(descripcion='Ajena', categoria=self.cat)
        DonacionUsuario.objects.create(donante=self.otro, donacion=ajena)
        r = self.client.get(reverse('dashboard_usuario'), {'tab': 'donaciones', 'don_estado': 'aprobada', 'don_sort': 'az'})
        self.assertEqual([d.descripcion for d in r.context['mis_donaciones']], ['Abrigo', 'Mesa'])
        self.assertEqual(r.context['stats']['total_don'], 3)
        self.assertEqual(r.context['stats']['don_aprobadas'], 2)
        self.assertNotContains(r, 'Ajena')
        r = self.client.get(reverse('dashboard_usuario'), {'don_buscar': 'zap', 'don_cat': '0'})
        self.assertEqual(len(r.context['mis_donaciones']), 1)

    # ── solicitudes ──
    def test_ciclo_solicitud(self):
        self.client.post(reverse('usuario_solicitud_crear'), {'descripcion': 'Necesito cobijas', 'idCategoria': self.cat.id})
        s = Solicitud.objects.get()
        self.assertEqual((s.solicitante, s.estado), (self.ana, 'pendiente'))
        self.client.post(reverse('usuario_solicitud_editar', args=[s.id]),
                         {'descripcion': 'Necesito dos cobijas', 'idCategoria': self.cat.id})
        s.refresh_from_db()
        self.assertEqual(s.descripcion, 'Necesito dos cobijas')
        self.client.force_login(self.otro)
        self.assertEqual(self.client.post(reverse('usuario_solicitud_cancelar', args=[s.id])).status_code, 404)
        self.client.force_login(self.ana)
        self.client.post(reverse('usuario_solicitud_cancelar', args=[s.id]))
        s.refresh_from_db()
        self.assertEqual(s.estado, 'cancelada')      # queda en el historial, como las visitas
        self.assertEqual(self.client.post(reverse('usuario_solicitud_cancelar', args=[s.id])).status_code, 404)

    # ── visitas ──
    def test_visitas_una_activa_cancelar_y_nota(self):
        manana = (date.today() + timedelta(days=1)).isoformat()
        datos = {'direccion': 'Calle 9 # 8-7', 'motivo': 'Verificar mi necesidad', 'fechaPreferida': manana}
        self.client.post(reverse('usuario_visita_crear'), datos)
        self.client.post(reverse('usuario_visita_crear'), datos)
        self.assertEqual(VisitaDomiciliaria.objects.count(), 1, 'solo una visita activa')
        v = VisitaDomiciliaria.objects.get()

        self.client.post(reverse('usuario_visita_nota', args=[v.id]), {'texto': 'Llegar después de las 3pm'})
        self.assertEqual(VisitaObservacion.objects.get().usuario, self.ana)
        html = self.client.get(reverse('dashboard_usuario'), {'tab': 'visitas'}).content.decode()
        self.assertTrue('Llegar después de las 3pm' in html)

        self.client.post(reverse('usuario_visita_cancelar', args=[v.id]))
        v.refresh_from_db()
        self.assertEqual(v.estado, 'cancelada')
        self.assertIsNotNone(v.fecha_resolucion)
        # ya cancelada: no se vuelve a cancelar y se puede pedir otra
        self.client.post(reverse('usuario_visita_cancelar', args=[v.id]))
        self.client.post(reverse('usuario_visita_crear'), datos)
        self.assertEqual(VisitaDomiciliaria.objects.count(), 2)

    def test_visita_fecha_pasada_rechazada(self):
        ayer = (date.today() - timedelta(days=1)).isoformat()
        self.client.post(reverse('usuario_visita_crear'),
                         {'direccion': 'Calle 9 # 8-7', 'motivo': 'Verificar mi necesidad', 'fechaPreferida': ayer})
        self.assertFalse(VisitaDomiciliaria.objects.exists())

    def test_nota_en_visita_ajena_404(self):
        v = VisitaDomiciliaria.objects.create(usuario=self.otro, direccion='x' * 6, motivo='y' * 11)
        self.assertEqual(self.client.post(reverse('usuario_visita_nota', args=[v.id]), {'texto': 'hola'}).status_code, 404)

    # ── perfil ──
    def test_perfil_campos_protegidos_no_cambian(self):
        self.client.post(reverse('usuario_perfil'), {
            'email': 'nuevo@x.co', 'telefono': '3109998888', 'direccion': 'Otra dirección 45',
            'necesidad': 'Alimentos', 'nombre': 'HACKEADO', 'num_documento': '1', 'rol': 'administrador'})
        self.ana.refresh_from_db()
        self.assertEqual((self.ana.email, self.ana.telefono, self.ana.necesidad), ('nuevo@x.co', '3109998888', 'Alimentos'))
        self.assertEqual((self.ana.nombre, self.ana.rol, self.ana.num_documento), ('Ana María', 'donante', 'ana'))

    def test_perfil_valida_email_unico_y_telefono(self):
        base = {'telefono': '3109998888', 'direccion': 'Otra dirección 45'}
        self.client.post(reverse('usuario_perfil'), {**base, 'email': 'otro@x.co'})
        self.client.post(reverse('usuario_perfil'), {**base, 'email': 'ok@x.co', 'telefono': '123'})
        self.ana.refresh_from_db()
        self.assertEqual(self.ana.email, 'ana@x.co')

    def test_cambio_de_clave(self):
        base = {'email': 'ana@x.co', 'telefono': '3001234567', 'direccion': 'Calle 1 # 2-3'}
        # clave actual incorrecta
        self.client.post(reverse('usuario_perfil'), {**base, 'password_actual': 'mala', 'password': 'Nueva456*', 'password_confirmation': 'Nueva456*'})
        self.ana.refresh_from_db(); self.assertTrue(self.ana.check_password('Clave123*'))
        # no coinciden
        self.client.post(reverse('usuario_perfil'), {**base, 'password_actual': 'Clave123*', 'password': 'Nueva456*', 'password_confirmation': 'otra'})
        self.ana.refresh_from_db(); self.assertTrue(self.ana.check_password('Clave123*'))
        # correcto: cambia y la sesión sigue abierta
        self.client.post(reverse('usuario_perfil'), {**base, 'password_actual': 'Clave123*', 'password': 'Nueva456*', 'password_confirmation': 'Nueva456*'})
        self.ana.refresh_from_db(); self.assertTrue(self.ana.check_password('Nueva456*'))
        self.assertEqual(self.client.get(reverse('dashboard_usuario')).status_code, 200)

    # ── corrección de datos ──
    def _correccion(self, archivo, **extra):
        datos = {'campo': 'nombre', 'valorNuevo': 'Ana Maria', 'justificacion': 'Error de digitación', 'consentimiento': 'on', 'soporte': archivo}
        datos.update(extra)
        return self.client.post(reverse('usuario_perfil_correccion'), datos)

    def test_correccion_guarda_en_disco_privado_con_hash(self):
        from django.conf import settings
        self._correccion(SimpleUploadedFile('cedula.png', PNG, content_type='image/png'))
        c = CorreccionDatos.objects.get()
        self.assertEqual((c.estado, c.campo, c.valor_anterior, c.consentimiento), ('pendiente', 'nombre', 'Ana María', True))
        self.assertEqual(len(c.soporte_hash), 64)
        self.assertNotIn('cedula', c.soporte_ruta, 'no se conserva el nombre enviado por el usuario')
        self.assertTrue(os.path.exists(os.path.join(settings.PRIVATE_MEDIA_ROOT, c.soporte_ruta)))
        self.assertFalse(os.path.exists(os.path.join(settings.MEDIA_ROOT, c.soporte_ruta)), 'no debe ser público')
        self.ana.refresh_from_db(); self.assertEqual(self.ana.nombre, 'Ana María')

    def test_correccion_rechaza_soportes_invalidos(self):
        self._correccion(SimpleUploadedFile('virus.pdf', b'MZ\x90\x00 no soy pdf', content_type='application/pdf'))
        self._correccion(SimpleUploadedFile('c.exe', PNG, content_type='image/png'))
        self._correccion(SimpleUploadedFile('c.png', PNG + b'0' * (4 * 1024 * 1024), content_type='image/png'))
        self._correccion(SimpleUploadedFile('c.png', PNG, content_type='image/png'), consentimiento='')
        self.assertFalse(CorreccionDatos.objects.exists())

    # ── eventos / XSS ──
    def test_eventos_publicados_y_escape_en_json(self):
        Evento.objects.create(nombre='Jornada <script>alert(1)</script>', estado='publicado', fecha_inicio=date(2026, 12, 1), fecha_fin=date(2026, 12, 2))
        Evento.objects.create(nombre='Borrador oculto', estado='borrador')
        html = self.client.get(reverse('dashboard_usuario'), {'tab': 'eventos'}).content.decode()
        self.assertFalse('<script>alert(1)</script>' in html)
        self.assertFalse('Borrador oculto' in html)
        self.assertTrue('1 de diciembre de 2026' in html)
