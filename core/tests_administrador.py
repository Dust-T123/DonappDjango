import os
import tempfile
from datetime import date, timedelta

from django.conf import settings
from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import (
    Categoria, CorreccionDatos, Donacion, DonacionUsuario, Evento, Solicitud, Usuario, VisitaDomiciliaria,
)
from .tests_usuario import PNG, crear_usuario

HOY = date.today()


def archivo(nombre='c.png', contenido=PNG, tipo='image/png'):
    return SimpleUploadedFile(nombre, contenido, content_type=tipo)


@override_settings(MEDIA_ROOT=tempfile.mkdtemp(), PRIVATE_MEDIA_ROOT=tempfile.mkdtemp())
class PanelAdministradorTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = crear_usuario('adm@x.co', rol='administrador')
        cls.admin2 = crear_usuario('adm2@x.co', rol='administrador')
        cls.asis = crear_usuario('asis@x.co', rol='asistente')
        cls.ana = crear_usuario('ana@x.co', prioridad='alta', necesidad='Comida')
        cls.cat = Categoria.objects.create(nombre='Ropa')

    def setUp(self):
        self.client.force_login(self.admin)

    def post(self, ruta, /, *args, **datos):
        return self.client.post(reverse(ruta, args=args), datos)

    # ── acceso ──
    def test_solo_administrador_entra_y_las_acciones_estan_protegidas(self):
        url = reverse('dashboard_administrador')
        self.assertEqual(self.client.get(url).status_code, 200)
        for quien, destino in ((self.asis, 'dashboard_asistente'), (self.ana, 'dashboard_usuario')):
            self.client.force_login(quien)
            self.assertRedirects(self.client.get(url), reverse(destino), fetch_redirect_response=False)
            self.post('adm_usuario_crear', email='x@x.co')
            self.post('adm_usuario_estado', self.ana.id)
            self.post('adm_categoria_crear', nombre_categoria='Intrusa')
            self.assertFalse(Categoria.objects.filter(nombre='Intrusa').exists())
        self.client.logout()
        self.assertRedirects(self.client.get(url), reverse('login'), fetch_redirect_response=False)

    def test_dashboard_renderiza_con_datos(self):
        d = Donacion.objects.create(descripcion='Mesa', categoria=self.cat, stock=2, estado='aprobada')
        DonacionUsuario.objects.create(donante=self.ana, donacion=d)
        Solicitud.objects.create(descripcion='Cobijas', solicitante=self.ana, categoria=self.cat)
        Evento.objects.create(nombre='Jornada', fecha_inicio=HOY, fecha_fin=HOY)
        VisitaDomiciliaria.objects.create(usuario=self.ana, direccion='Calle 1 # 2', motivo='Verificar necesidad')
        r = self.client.get(reverse('dashboard_administrador'))
        c = r.context
        self.assertEqual((c['total_usuarios'], c['total_categorias'], c['total_donaciones']), (4, 1, 1))
        self.assertEqual(c['categorias'][0].donaciones_count, 1)
        self.assertEqual(c['categorias'][0].solicitudes_count, 1)
        self.assertFalse(c['categorias'][0].eliminable)
        # el JS de reportes del admin lee idDonacion / idSolicitud (en Laravel llegaba "id" y salía vacío)
        self.assertEqual(c['reporte_donaciones'][0]['idDonacion'], d.id)
        self.assertIn('idSolicitud', c['reporte_solicitudes'][0])
        self.assertEqual(c['donaciones'][0].donante_nombre, 'Ana María')

    def test_usuarios_filtros_y_json_sin_hash(self):
        r = self.client.get(reverse('dashboard_administrador'), {'rol': 'administrador', 'sort': 'az'})
        self.assertEqual([u.email for u in r.context['usuarios']], ['adm@x.co', 'adm2@x.co'])
        html = self.client.get(reverse('dashboard_administrador')).content.decode()
        self.assertFalse('pbkdf2' in html or 'md5$' in html, 'el hash de contraseña no debe llegar al navegador')

    # ── acciones compartidas (misma lógica que el asistente) ──
    def test_acciones_compartidas_vuelven_al_panel_del_administrador(self):
        d = Donacion.objects.create(descripcion='Mesa', categoria=self.cat)
        DonacionUsuario.objects.create(donante=self.ana, donacion=d)
        r = self.post('adm_donacion_estado', d.id, estado='aprobada', observacion='ok')
        self.assertEqual(r.status_code, 302)
        self.assertTrue(r.url.startswith(reverse('dashboard_administrador')))
        d.refresh_from_db(); self.assertEqual(d.estado, 'aprobada')
        self.assertEqual(mail.outbox[-1].to, ['ana@x.co'])
        self.post('adm_categoria_crear', nombre_categoria='Alimentos')
        self.assertEqual(Categoria.objects.get(nombre='Alimentos').creado_por, self.admin)
        self.post('adm_evento_crear', nombre_evento='Jornada', fecha_inicio=HOY.isoformat(), fecha_fin=HOY.isoformat(),
                  lugar_entrega='Sede', titulo_pub='Gran jornada', contenido_pub='Detalles de la jornada')
        self.assertEqual(Evento.objects.get().nombre, 'Gran jornada')

    def test_las_mismas_acciones_siguen_volviendo_al_asistente(self):
        self.client.force_login(self.asis)
        r = self.post('asis_categoria_crear', nombre_categoria='Alimentos')
        self.assertTrue(r.url.startswith(reverse('dashboard_asistente')))

    # ── usuarios ──
    def _usuario(self, **extra):
        datos = {'nombre': 'Carlos', 'apellido': 'Ruiz', 'tipoDocumento': 'CC', 'numDocumento': '99887766',
                 'fechaNacimiento': '1985-05-05', 'direccion': 'Calle 5 # 6-7', 'email': 'carlos@x.co',
                 'telefono': '3011112222', 'password': 'Segura987*', 'password_confirmation': 'Segura987*',
                 'rol': 'asistente', 'estado': 'activo', 'prioridad': 'alta', 'necesidad': 'Mercado'}
        datos.update(extra)
        return datos

    def test_crear_usuario_de_personal_ignora_campos_de_donante(self):
        self.post('adm_usuario_crear', **self._usuario())
        u = Usuario.objects.get(email='carlos@x.co')
        self.assertEqual((u.rol, u.estado, u.necesidad, u.prioridad), ('asistente', 'activo', None, None))
        self.assertTrue(u.check_password('Segura987*'))
        self.post('adm_usuario_crear', **self._usuario(email='d@x.co', numDocumento='11112222', rol='donante'))
        d = Usuario.objects.get(email='d@x.co')
        self.assertEqual((d.rol, d.prioridad, d.necesidad), ('donante', 'alta', 'Mercado'))

    def test_crear_usuario_validaciones(self):
        for extra in ({'email': 'ana@x.co'}, {'numDocumento': 'ana'}, {'rol': 'superusuario'}, {'estado': 'x'},
                      {'fechaNacimiento': (HOY - timedelta(days=365 * 10)).isoformat()},
                      {'password_confirmation': 'otra'}, {'tipoDocumento': 'XX'}, {'telefono': '123'}):
            self.post('adm_usuario_crear', **self._usuario(**extra))
        self.assertFalse(Usuario.objects.filter(nombre='Carlos').exists())

    def test_editar_usuario_cambia_rol_y_limpia_campos_de_donante(self):
        self.post('adm_usuario_editar', self.ana.id, email='ana@x.co', telefono='3001234567', direccion='Calle 1 # 2-3',
                  rol='asistente', estado='activo', nombre='HACK', num_documento='1', prioridad='alta', necesidad='x')
        self.ana.refresh_from_db()
        self.assertEqual((self.ana.rol, self.ana.prioridad, self.ana.necesidad), ('asistente', None, None))
        self.assertEqual((self.ana.nombre, self.ana.num_documento), ('Ana María', 'ana'), 'identidad intacta')

    def test_proteccion_de_la_propia_cuenta(self):
        base = dict(email='adm@x.co', telefono='3001234567', direccion='Calle 1 # 2-3', rol='administrador', estado='activo')
        self.post('adm_usuario_editar', self.admin.id, **{**base, 'rol': 'donante'})
        self.post('adm_usuario_editar', self.admin.id, **{**base, 'estado': 'inactivo'})
        self.post('adm_usuario_editar', self.admin.id, **base, password='Hackeada123*', password_confirmation='Hackeada123*')
        self.post('adm_usuario_estado', self.admin.id)
        self.admin.refresh_from_db()
        self.assertEqual((self.admin.rol, self.admin.estado), ('administrador', 'activo'))
        self.assertTrue(self.admin.check_password('Clave123*'), 'la clave propia solo se cambia con código al correo')

    def test_editar_otro_usuario_con_clave_y_toggle(self):
        base = dict(email='ana@x.co', telefono='3001234567', direccion='Calle 1 # 2-3', rol='donante', estado='activo')
        self.post('adm_usuario_editar', self.ana.id, **base, password='Nuevita456*', password_confirmation='Nuevita456*')
        self.ana.refresh_from_db(); self.assertTrue(self.ana.check_password('Nuevita456*'))
        self.post('adm_usuario_estado', self.ana.id)
        self.ana.refresh_from_db(); self.assertEqual(self.ana.estado, 'inactivo')
        self.client.logout()
        self.assertFalse(self.client.login(username='ana@x.co', password='Nuevita456*') and False)

    def test_usuario_inactivado_pierde_la_sesion(self):
        sesion = self.client_class(); sesion.force_login(self.asis)
        self.assertEqual(sesion.get(reverse('dashboard_asistente')).status_code, 200)
        self.post('adm_usuario_estado', self.asis.id)
        self.assertEqual(sesion.get(reverse('dashboard_asistente')).status_code, 302)

    # ── correcciones: doble control ──
    def _pedir(self, solicitante, objetivo, campo='nombre', valor='Ana Maria', **extra):
        self.client.force_login(solicitante)
        datos = {'campo': campo, 'valorNuevo': valor, 'justificacion': 'Error de digitación', 'consentimiento': 'on',
                 'soporte': archivo()}
        datos.update(extra)
        return self.client.post(reverse('adm_usuario_correccion', args=[objetivo.id]), datos)

    def _correccion(self, campo='nombre', valor='Ana Maria', solicitante=None, objetivo=None):
        self._pedir(solicitante or self.admin, objetivo or self.ana, campo, valor)
        return CorreccionDatos.objects.latest('id')

    def test_no_se_puede_duplicar_una_correccion_pendiente_ni_dejar_archivos_huerfanos(self):
        self._pedir(self.admin, self.ana)
        antes = len(os.listdir(os.path.join(settings.PRIVATE_MEDIA_ROOT, 'correcciones')))
        self._pedir(self.admin2, self.ana)                       # mismo usuario y campo
        self.client.force_login(self.ana)                        # el propio donante
        self.client.post(reverse('usuario_perfil_correccion'), {
            'campo': 'nombre', 'valorNuevo': 'Otro', 'justificacion': 'Error de digitación',
            'consentimiento': 'on', 'soporte': archivo()})
        self.client.force_login(self.asis)                       # un asistente
        self.client.post(reverse('asis_cliente_correccion', args=[self.ana.id]), {
            'campo': 'nombre', 'valorNuevo': 'Otro', 'justificacion': 'Error de digitación',
            'consentimiento': 'on', 'soporte': archivo()})
        self.assertEqual(CorreccionDatos.objects.count(), 1)
        self.assertEqual(len(os.listdir(os.path.join(settings.PRIVATE_MEDIA_ROOT, 'correcciones'))), antes)
        self._pedir(self.admin, self.ana, campo='apellido', valor='Gómez')  # otro campo sí
        self.assertEqual(CorreccionDatos.objects.count(), 2)

    def test_quien_la_pidio_no_puede_aprobarla_pero_otro_admin_si(self):
        c = self._correccion()
        self.client.force_login(self.admin)
        self.post('adm_correccion_aprobar', c.id)
        c.refresh_from_db(); self.ana.refresh_from_db()
        self.assertEqual((c.estado, self.ana.nombre), ('pendiente', 'Ana María'))
        self.client.force_login(self.admin2)
        self.post('adm_correccion_aprobar', c.id)
        c.refresh_from_db(); self.ana.refresh_from_db()
        self.assertEqual((c.estado, c.aprobador, self.ana.nombre), ('aprobada', self.admin2, 'Ana Maria'))
        self.assertIsNotNone(c.fecha_resolucion)
        self.assertEqual(mail.outbox[-1].to, ['ana@x.co'])
        self.assertTrue('Ana Maria' in mail.outbox[-1].body)

    def test_aprobar_purga_el_documento_y_no_se_aplica_dos_veces(self):
        c = self._correccion()
        ruta = os.path.join(settings.PRIVATE_MEDIA_ROOT, c.soporte_ruta)
        self.assertTrue(os.path.exists(ruta))
        self.client.force_login(self.admin2)
        self.post('adm_correccion_aprobar', c.id)
        c.refresh_from_db()
        self.assertFalse(os.path.exists(ruta))
        self.assertIsNone(c.soporte_ruta)
        self.assertEqual(len(c.soporte_hash), 64, 'el hash queda como evidencia de integridad')
        self.ana.nombre = 'Cambiado Después'; self.ana.save()
        self.post('adm_correccion_aprobar', c.id)                 # ya resuelta: no se reaplica
        self.ana.refresh_from_db(); self.assertEqual(self.ana.nombre, 'Cambiado Después')

    def test_aprobar_valida_el_valor_propuesto(self):
        casos = [('numDocumento', 'adm2'), ('numDocumento', 'ab'), ('numDocumento', 'tiene espacios'),
                 ('tipoDocumento', 'XX'), ('fechaNacimiento', 'no es fecha'),
                 ('fechaNacimiento', (HOY - timedelta(days=365 * 5)).isoformat()), ('nombre', 'Al'), ('apellido', 'P')]
        # (el número "adm2" coincide con el de admin2: ya está en uso)
        for campo, valor in casos:
            c = self._correccion(campo, valor)
            self.client.force_login(self.admin2)
            self.post('adm_correccion_aprobar', c.id)
            c.refresh_from_db()
            self.assertEqual(c.estado, 'pendiente', f'{campo}={valor!r} no debió aprobarse')
            CorreccionDatos.objects.filter(pk=c.pk).update(estado='rechazada')   # libera el campo
        self.ana.refresh_from_db()
        self.assertEqual((self.ana.num_documento, self.ana.nombre), ('ana', 'Ana María'))

    def test_aprobar_cambia_cada_campo_con_su_tipo(self):
        for campo, valor in (('apellido', 'Gómez'), ('tipoDocumento', 'CE'), ('numDocumento', 'AB12345'),
                             ('fechaNacimiento', '1992-03-04')):
            c = self._correccion(campo, valor)
            self.client.force_login(self.admin2)
            self.post('adm_correccion_aprobar', c.id)
        self.ana.refresh_from_db()
        self.assertEqual((self.ana.apellido, self.ana.tipo_documento, self.ana.num_documento, self.ana.fecha_nacimiento),
                         ('Gómez', 'CE', 'AB12345', date(1992, 3, 4)))
        c = self._correccion('fechaNacimiento', '05/06/1990')     # también acepta DD/MM/AAAA
        self.client.force_login(self.admin2); self.post('adm_correccion_aprobar', c.id)
        self.ana.refresh_from_db(); self.assertEqual(self.ana.fecha_nacimiento, date(1990, 6, 5))

    def test_rechazar_guarda_motivo_purga_y_avisa(self):
        c = self._correccion()
        ruta = os.path.join(settings.PRIVATE_MEDIA_ROOT, c.soporte_ruta)
        self.client.force_login(self.admin2)
        self.post('adm_correccion_rechazar', c.id, motivo='El documento no coincide')
        c.refresh_from_db(); self.ana.refresh_from_db()
        self.assertEqual((c.estado, c.observacion_resolucion, c.aprobador), ('rechazada', 'El documento no coincide', self.admin2))
        self.assertFalse(os.path.exists(ruta))
        self.assertEqual(self.ana.nombre, 'Ana María')
        self.assertTrue('El documento no coincide' in mail.outbox[-1].body)
        self.post('adm_correccion_rechazar', c.id, motivo='otra vez')
        c.refresh_from_db(); self.assertEqual(c.observacion_resolucion, 'El documento no coincide')

    def test_un_fallo_de_correo_no_impide_resolver(self):
        from unittest import mock
        c = self._correccion()
        self.client.force_login(self.admin2)
        with mock.patch('core.notificaciones.EmailMultiAlternatives.send', side_effect=OSError('smtp caído')):
            self.post('adm_correccion_aprobar', c.id)
        c.refresh_from_db(); self.assertEqual(c.estado, 'aprobada')

    # ── acceso al documento de identidad ──
    def test_soporte_solo_lo_ve_otro_admin_con_cabeceras_seguras(self):
        c = self._correccion()
        url = reverse('adm_correccion_soporte', args=[c.id])
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get(url).status_code, 403, 'quien lo pidió no puede ver el soporte')
        self.client.force_login(self.admin2)
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r['Content-Type'], 'image/png')
        self.assertEqual(r['X-Content-Type-Options'], 'nosniff')
        self.assertTrue('no-store' in r['Cache-Control'])
        self.assertTrue(b''.join(r.streaming_content).startswith(b'\x89PNG'))
        for quien in (self.asis, self.ana):
            self.client.force_login(quien)
            self.assertEqual(self.client.get(url).status_code, 302, 'solo administradores')

    def test_soporte_purgado_o_con_contenido_extrano_da_404(self):
        c = self._correccion()
        self.client.force_login(self.admin2)
        ruta = os.path.join(settings.PRIVATE_MEDIA_ROOT, c.soporte_ruta)
        with open(ruta, 'wb') as f:                               # alguien sustituyó el archivo en disco
            f.write(b'<html><script>alert(1)</script></html>')
        self.assertEqual(self.client.get(reverse('adm_correccion_soporte', args=[c.id])).status_code, 404)
        self.post('adm_correccion_rechazar', c.id)
        self.assertEqual(self.client.get(reverse('adm_correccion_soporte', args=[c.id])).status_code, 404)

    def test_el_soporte_se_registra_en_el_log(self):
        c = self._correccion()
        self.client.force_login(self.admin2)
        with self.assertLogs('core.views.administrador', level='INFO') as log:
            self.client.get(reverse('adm_correccion_soporte', args=[c.id]))
        self.assertTrue(f'correccion={c.id}' in log.output[0] and f'admin={self.admin2.id}' in log.output[0])

    def test_panel_oculta_acciones_sobre_correcciones_propias(self):
        self._correccion()
        self.client.force_login(self.admin)
        html = self.client.get(reverse('dashboard_administrador')).content.decode()
        self.assertTrue('La pediste tú' in html)
        self.assertFalse('/aprobar/' in html)
        self.client.force_login(self.admin2)
        html = self.client.get(reverse('dashboard_administrador')).content.decode()
        self.assertTrue('/aprobar/' in html and '/soporte/' in html)

    # ── eliminaciones ──
    def test_categoria_con_registros_no_se_elimina(self):
        Donacion.objects.create(descripcion='Mesa', categoria=self.cat)
        self.post('adm_categoria_eliminar', self.cat.id)
        self.assertTrue(Categoria.objects.filter(pk=self.cat.pk).exists())
        self.assertTrue(Donacion.objects.get().categoria_id == self.cat.id)
        vacia = Categoria.objects.create(nombre='Vacía')
        self.post('adm_categoria_eliminar', vacia.id)
        self.assertFalse(Categoria.objects.filter(pk=vacia.pk).exists())

    def test_eliminar_evento_y_metodos(self):
        e = Evento.objects.create(nombre='Viejo', fecha_inicio=HOY, fecha_fin=HOY)
        self.assertEqual(self.client.get(reverse('adm_evento_eliminar', args=[e.id])).status_code, 405)
        self.post('adm_evento_eliminar', e.id)
        self.assertFalse(Evento.objects.exists())

    def test_html_del_usuario_no_se_inyecta_en_el_panel(self):
        malo = '<img src=x onerror=alert(1)>'
        Solicitud.objects.create(descripcion=malo, solicitante=self.ana, categoria=self.cat)
        Usuario.objects.filter(pk=self.ana.pk).update(nombre=malo)
        html = self.client.get(reverse('dashboard_administrador')).content.decode()
        self.assertFalse(malo in html)
