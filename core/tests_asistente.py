import json
import tempfile
import time
from datetime import date, timedelta
from unittest import mock

from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import (
    Categoria, CorreccionDatos, Donacion, DonacionUsuario, Evento, Solicitud, Usuario,
    VisitaDomiciliaria, VisitaObservacion,
)
from .tests_usuario import PNG, crear_usuario

HOY = date.today()


@override_settings(MEDIA_ROOT=tempfile.mkdtemp(), PRIVATE_MEDIA_ROOT=tempfile.mkdtemp())
class PanelAsistenteTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.asis = crear_usuario('asis@x.co', rol='asistente')
        cls.admin = crear_usuario('adm@x.co', rol='administrador')
        cls.ana = crear_usuario('ana@x.co', prioridad='baja', necesidad='Comida')
        cls.beto = crear_usuario('beto@x.co', nombre='Beto', prioridad='urgente', necesidad='Techo')
        cls.sin_prio = crear_usuario('sin@x.co', nombre='Zoe')
        cls.cat = Categoria.objects.create(nombre='Ropa')
        cls.cat2 = Categoria.objects.create(nombre='Alimentos')

    def setUp(self):
        self.client.force_login(self.asis)

    def post(self, ruta, /, *args, **datos):
        return self.client.post(reverse(ruta, args=args), datos)

    # ── acceso ──
    def test_solo_asistente_entra(self):
        url = reverse('dashboard_asistente')
        self.assertEqual(self.client.get(url).status_code, 200)
        for quien, destino in ((self.ana, 'dashboard_usuario'), (self.admin, 'dashboard_administrador')):
            self.client.force_login(quien)
            self.assertRedirects(self.client.get(url), reverse(destino), fetch_redirect_response=False)
        self.client.logout()
        self.assertRedirects(self.client.get(url), reverse('login'), fetch_redirect_response=False)

    def test_acciones_bloqueadas_para_donante_y_exigen_post(self):
        self.client.force_login(self.ana)
        self.post('asis_categoria_crear', nombre_categoria='Juguetes')
        self.assertFalse(Categoria.objects.filter(nombre='Juguetes').exists())
        self.client.force_login(self.asis)
        self.assertEqual(self.client.get(reverse('asis_categoria_crear')).status_code, 405)

    # ── dashboard ──
    def test_dashboard_renderiza_con_datos_en_todas_las_secciones(self):
        d = Donacion.objects.create(descripcion='Camisas', categoria=self.cat, stock=4, estado='aprobada')
        DonacionUsuario.objects.create(donante=self.ana, donacion=d)
        Solicitud.objects.create(descripcion='Cobijas', solicitante=self.ana, categoria=self.cat)
        Evento.objects.create(nombre='Jornada', estado='publicado', fecha_inicio=HOY, fecha_fin=HOY)
        v = VisitaDomiciliaria.objects.create(usuario=self.ana, direccion='Calle 1 # 2', motivo='Verificar necesidad')
        VisitaObservacion.objects.create(visita=v, usuario=self.asis, texto='Nota inicial')
        r = self.client.get(reverse('dashboard_asistente'))
        self.assertEqual(r.status_code, 200)
        c = r.context
        self.assertEqual((c['total_donaciones'], c['total_solicitudes'], c['total_aprobadas']), (1, 1, 1))
        self.assertEqual(c['total_pendientes'], 1)
        self.assertEqual(c['total_donantes'], 3)
        self.assertEqual(c['total_visitas_pendientes'], 1)
        self.assertEqual(c['total_unidades_inventario'], 4)
        self.assertEqual(c['donaciones'][0].donante_nombre, 'Ana María')
        self.assertEqual(c['visitas'][0].ultima_nota, 'Nota inicial')

    def test_donantes_solo_donantes_y_orden_por_prioridad(self):
        r = self.client.get(reverse('dashboard_asistente'), {'cli_sort': 'prioridad'})
        self.assertEqual([x.email for x in r.context['donantes']], ['beto@x.co', 'ana@x.co', 'sin@x.co'])
        self.assertFalse(any(x.rol != 'donante' for x in r.context['donantes']))
        r = self.client.get(reverse('dashboard_asistente'), {'cli_search': 'zoe'})
        self.assertEqual([x.email for x in r.context['donantes']], ['sin@x.co'])
        r = self.client.get(reverse('dashboard_asistente'), {'cli_prioridad': 'urgente'})
        self.assertEqual([x.email for x in r.context['donantes']], ['beto@x.co'])

    def test_solicitudes_orden_por_prioridad_y_filtros(self):
        for u, desc in ((self.ana, 'S-baja'), (self.beto, 'S-urgente'), (self.sin_prio, 'S-sin')):
            Solicitud.objects.create(descripcion=desc, solicitante=u, categoria=self.cat)
        r = self.client.get(reverse('dashboard_asistente'), {'sol_sort': 'prioridad'})
        self.assertEqual([s.descripcion for s in r.context['solicitudes']], ['S-urgente', 'S-baja', 'S-sin'])
        r = self.client.get(reverse('dashboard_asistente'), {'sol_search': 'beto'})
        self.assertEqual([s.descripcion for s in r.context['solicitudes']], ['S-urgente'])

    def test_donaciones_busqueda_por_donante_y_sin_duplicados(self):
        d = Donacion.objects.create(descripcion='Mesa', categoria=self.cat)
        DonacionUsuario.objects.create(donante=self.ana, donacion=d)
        DonacionUsuario.objects.create(donante=self.beto, donacion=d)
        r = self.client.get(reverse('dashboard_asistente'), {'don_search': 'Ana'})
        self.assertEqual(len(r.context['donaciones']), 1)
        r = self.client.get(reverse('dashboard_asistente'), {'don_search': 'a'})
        self.assertEqual(len(r.context['donaciones']), 1, 'una donación con 2 donantes no debe repetirse')

    def test_inventario_agrupa_solo_aprobadas(self):
        for stock, estado in ((3, 'aprobada'), (2, 'aprobada'), (9, 'pendiente')):
            Donacion.objects.create(descripcion='Cobijas', categoria=self.cat, stock=stock, estado=estado)
        Donacion.objects.create(descripcion='Arroz', categoria=self.cat2, stock=10, estado='aprobada')
        r = self.client.get(reverse('dashboard_asistente'))
        inv = {i['descripcion']: (i['total_stock'], i['num_donaciones']) for i in r.context['inventario']}
        self.assertEqual(inv, {'Cobijas': (5, 2), 'Arroz': (10, 1)})
        self.assertEqual(r.context['inventario'][0]['descripcion'], 'Arroz', 'mayor cantidad primero')
        self.assertEqual(r.context['total_unidades_inventario'], 15)

    def test_html_del_usuario_no_se_inyecta_en_la_pagina(self):
        malo = '<img src=x onerror=alert(1)>'
        Solicitud.objects.create(descripcion=malo, solicitante=self.ana, categoria=self.cat)
        html = self.client.get(reverse('dashboard_asistente')).content.decode()
        self.assertFalse(malo in html)

    def test_pestana_invalida_no_rompe(self):
        self.assertEqual(self.client.get(reverse('dashboard_asistente'), {'tab': 'nada'}).status_code, 200)

    # ── categorías ──
    def test_categorias_validaciones(self):
        for nombre in ('ab', 'Con 123', 'ropa', ' RoPa ', 'Ropa!'):
            self.post('asis_categoria_crear', nombre_categoria=nombre)
        self.assertEqual(Categoria.objects.count(), 2)
        self.post('asis_categoria_crear', nombre_categoria='Útiles (escolares) - 2024'.replace(' 2024', ''))
        self.assertEqual(Categoria.objects.get(nombre__startswith='Útiles').creado_por, self.asis)

    def test_editar_categoria_permite_su_propio_nombre_pero_no_el_de_otra(self):
        self.post('asis_categoria_editar', self.cat.id, nombre_categoria='Ropa')
        self.post('asis_categoria_editar', self.cat.id, nombre_categoria='alimentos')
        self.cat.refresh_from_db(); self.assertEqual(self.cat.nombre, 'Ropa')
        self.post('asis_categoria_editar', self.cat.id, nombre_categoria='Ropa de abrigo')
        self.cat.refresh_from_db(); self.assertEqual(self.cat.nombre, 'Ropa de abrigo')

    # ── eventos ──
    def _evento(self, **extra):
        datos = {'nombre_evento': 'Jornada', 'fecha_inicio': HOY.isoformat(), 'fecha_fin': HOY.isoformat(),
                 'lugar_entrega': 'Sede principal', 'titulo_pub': 'Gran jornada', 'contenido_pub': 'Detalles de la jornada'}
        datos.update(extra)
        return datos

    def test_crear_evento_y_reglas_de_fecha(self):
        self.post('asis_evento_crear', **self._evento(fecha_inicio=(HOY - timedelta(days=1)).isoformat()))
        self.post('asis_evento_crear', **self._evento(fecha_fin=(HOY - timedelta(days=1)).isoformat()))
        self.post('asis_evento_crear', **self._evento(fecha_inicio=(HOY + timedelta(days=3)).isoformat()))
        self.assertFalse(Evento.objects.exists())
        self.client.post(reverse('asis_evento_crear'), {**self._evento(estado_evento='publicado'),
                         'imagen_pub': SimpleUploadedFile('e.png', PNG, content_type='image/png')})
        e = Evento.objects.get()
        self.assertEqual((e.nombre, e.estado, e.fecha_publicacion), ('Gran jornada', 'publicado', HOY))
        self.assertTrue(e.imagen)

    def test_editar_evento_pasado_y_cambiar_estado(self):
        ayer = HOY - timedelta(days=2)
        e = Evento.objects.create(nombre='Viejo', fecha_inicio=ayer, fecha_fin=ayer, lugar='x' * 3)
        self.post('asis_evento_editar', e.id, **self._evento(fecha_inicio=ayer.isoformat(), fecha_fin=ayer.isoformat(),
                                                            titulo_pub='Nuevo título', estado_evento='finalizado'))
        e.refresh_from_db()
        self.assertEqual((e.nombre, e.estado), ('Nuevo título', 'finalizado'))
        self.post('asis_evento_estado', e.id, estado='publicado')
        self.post('asis_evento_estado', e.id, estado='inventado')
        e.refresh_from_db(); self.assertEqual(e.estado, 'publicado')

    # ── donaciones / solicitudes ──
    def test_rechazar_exige_observacion_y_aprobar_notifica(self):
        d = Donacion.objects.create(descripcion='Mesa', categoria=self.cat)
        DonacionUsuario.objects.create(donante=self.ana, donacion=d)
        self.post('asis_donacion_estado', d.id, estado='rechazada', observacion='  ')
        d.refresh_from_db(); self.assertEqual(d.estado, 'pendiente')
        self.assertEqual(len(mail.outbox), 0)
        self.post('asis_donacion_estado', d.id, estado='aprobada', observacion='Todo bien')
        d.refresh_from_db(); self.assertEqual((d.estado, d.observacion), ('aprobada', 'Todo bien'))
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ['ana@x.co'])
        self.assertTrue('APROBADA' in mail.outbox[0].body)

    def test_fallo_de_correo_no_impide_el_cambio_de_estado(self):
        d = Donacion.objects.create(descripcion='Mesa', categoria=self.cat)
        DonacionUsuario.objects.create(donante=self.ana, donacion=d)
        with mock.patch('core.notificaciones.EmailMultiAlternatives.send', side_effect=OSError('smtp caído')):
            r = self.post('asis_donacion_estado', d.id, estado='aprobada')
        self.assertEqual(r.status_code, 302)
        d.refresh_from_db(); self.assertEqual(d.estado, 'aprobada')

    def test_estado_solicitud_asigna_gestor(self):
        s = Solicitud.objects.create(descripcion='Cobijas', solicitante=self.ana, categoria=self.cat)
        self.assertIsNone(s.gestor)
        self.post('asis_solicitud_estado', s.id, estado='aprobada', observacion='ok')
        s.refresh_from_db(); self.assertEqual((s.estado, s.gestor), ('aprobada', self.asis))
        self.assertEqual(mail.outbox[-1].to, ['ana@x.co'])

    def test_observacion_en_correo_va_escapada_en_html(self):
        s = Solicitud.objects.create(descripcion='Cobijas', solicitante=self.ana, categoria=self.cat)
        self.post('asis_solicitud_estado', s.id, estado='aprobada', observacion='<b>hola</b>')
        html = mail.outbox[-1].alternatives[0][0]
        self.assertTrue('&lt;b&gt;hola&lt;/b&gt;' in html)

    # ── donantes ──
    def _donante(self, **extra):
        datos = {'nombre': 'Carlos', 'apellido': 'Ruiz', 'tipoDocumento': 'CC', 'numDocumento': '99887766',
                 'fechaNacimiento': '1985-05-05', 'direccion': 'Calle 5 # 6-7', 'email': 'carlos@x.co',
                 'telefono': '3011112222', 'password': 'Segura987*', 'password_confirmation': 'Segura987*',
                 'prioridad': 'alta', 'necesidad': 'Mercado'}
        datos.update(extra)
        return datos

    def test_crear_donante(self):
        self.post('asis_donante_crear', **self._donante())
        c = Usuario.objects.get(email='carlos@x.co')
        self.assertEqual((c.rol, c.estado, c.prioridad), ('donante', 'activo', 'alta'))
        self.assertTrue(c.check_password('Segura987*'))

    def test_crear_donante_rechaza_duplicados_menores_y_rol_forzado(self):
        self.post('asis_donante_crear', **self._donante(email='ana@x.co'))
        self.post('asis_donante_crear', **self._donante(numDocumento='ana'))
        self.post('asis_donante_crear', **self._donante(fechaNacimiento=(HOY - timedelta(days=365 * 10)).isoformat()))
        self.post('asis_donante_crear', **self._donante(prioridad='suprema'))
        self.post('asis_donante_crear', **self._donante(password_confirmation='otra'))
        self.assertFalse(Usuario.objects.filter(email='carlos@x.co').exists())
        self.post('asis_donante_crear', **self._donante(rol='administrador'))
        self.assertEqual(Usuario.objects.get(email='carlos@x.co').rol, 'donante')

    def test_editar_donante_no_toca_datos_sensibles(self):
        self.post('asis_donante_editar', self.ana.id, email='nuevo@x.co', telefono='3200000000',
                  direccion='Otra dirección 99', necesidad='Ropa', prioridad='media', nombre='HACK',
                  num_documento='1', rol='administrador')
        self.ana.refresh_from_db()
        self.assertEqual((self.ana.email, self.ana.prioridad, self.ana.necesidad), ('nuevo@x.co', 'media', 'Ropa'))
        self.assertEqual((self.ana.nombre, self.ana.rol, self.ana.num_documento), ('Ana María', 'donante', 'ana'))

    def test_editar_donante_clave_opcional(self):
        base = dict(email='ana@x.co', telefono='3001234567', direccion='Calle 1 # 2-3')
        self.post('asis_donante_editar', self.ana.id, **base)
        self.ana.refresh_from_db(); self.assertTrue(self.ana.check_password('Clave123*'))
        self.post('asis_donante_editar', self.ana.id, **base, password='Nuevita456*', password_confirmation='x')
        self.ana.refresh_from_db(); self.assertTrue(self.ana.check_password('Clave123*'))
        self.post('asis_donante_editar', self.ana.id, **base, password='Nuevita456*', password_confirmation='Nuevita456*')
        self.ana.refresh_from_db(); self.assertTrue(self.ana.check_password('Nuevita456*'))

    def test_asistente_no_puede_gestionar_a_administradores_ni_otros_asistentes(self):
        """En Laravel cualquier id servía: un asistente podía cambiar el correo/clave de un admin."""
        otro_asis = crear_usuario('otro@x.co', rol='asistente')
        for objetivo in (self.admin, otro_asis):
            self.assertEqual(self.post('asis_donante_editar', objetivo.id, email='robado@x.co', telefono='3001234567',
                                       direccion='Calle 1 # 2-3', password='Hackeado123*',
                                       password_confirmation='Hackeado123*').status_code, 404)
            self.assertEqual(self.post('asis_donante_estado', objetivo.id).status_code, 404)
            self.assertEqual(self.client.get(reverse('asis_donante_historial', args=[objetivo.id])).status_code, 404)
        self.admin.refresh_from_db()
        self.assertEqual((self.admin.email, self.admin.estado), ('adm@x.co', 'activo'))
        self.assertTrue(self.admin.check_password('Clave123*'))

    def test_toggle_estado_donante(self):
        self.post('asis_donante_estado', self.ana.id)
        self.ana.refresh_from_db(); self.assertEqual(self.ana.estado, 'inactivo')
        self.post('asis_donante_estado', self.ana.id)
        self.ana.refresh_from_db(); self.assertEqual(self.ana.estado, 'activo')

    def test_historial_donante_json(self):
        d = Donacion.objects.create(descripcion='Mesa', categoria=self.cat)
        DonacionUsuario.objects.create(donante=self.ana, donacion=d)
        Solicitud.objects.create(descripcion='Cobijas', solicitante=self.ana, categoria=self.cat)
        Solicitud.objects.create(descripcion='Ajena', solicitante=self.beto, categoria=self.cat)
        datos = self.client.get(reverse('asis_donante_historial', args=[self.ana.id])).json()
        self.assertEqual([x['descripcion'] for x in datos['donaciones']], ['Mesa'])
        self.assertEqual([x['descripcion'] for x in datos['solicitudes']], ['Cobijas'])
        self.assertEqual(datos['donaciones'][0]['fecha'], HOY.strftime('%d/%m/%Y'))
        self.assertEqual(self.post('asis_donante_historial', self.ana.id).status_code, 405)

    def test_correccion_para_donante_y_perfil_propio(self):
        archivo = lambda: SimpleUploadedFile('c.png', PNG, content_type='image/png')
        base = {'campo': 'apellido', 'valorNuevo': 'Pérez Gómez', 'justificacion': 'Error de digitación',
                'consentimiento': 'on'}
        self.client.post(reverse('asis_donante_correccion', args=[self.ana.id]), {**base, 'soporte': archivo()})
        c = CorreccionDatos.objects.get()
        self.assertEqual((c.usuario, c.solicitante, c.valor_anterior, c.estado), (self.ana, self.asis, 'Pérez', 'pendiente'))
        self.client.post(reverse('asis_perfil_correccion'), {**base, 'soporte': archivo()})
        self.assertEqual(CorreccionDatos.objects.filter(usuario=self.asis, solicitante=self.asis).count(), 1)
        self.client.post(reverse('asis_donante_correccion', args=[self.admin.id]), {**base, 'soporte': archivo()})
        self.assertEqual(CorreccionDatos.objects.count(), 2, 'no se puede pedir corrección sobre un admin')
        self.ana.refresh_from_db(); self.assertEqual(self.ana.apellido, 'Pérez')

    # ── visitas ──
    def test_visita_cambio_de_estado_y_constancia(self):
        v = VisitaDomiciliaria.objects.create(usuario=self.ana, direccion='Calle 1 # 2', motivo='Verificar necesidad')
        self.post('asis_visita_estado', v.id, estado='pendiente')
        v.refresh_from_db(); self.assertEqual(v.estado, 'pendiente')
        self.post('asis_visita_estado', v.id, estado='aprobada', observacion='Se visitará el lunes')
        v.refresh_from_db()
        self.assertEqual((v.estado, v.gestor), ('aprobada', self.asis))
        self.assertIsNotNone(v.fecha_resolucion)
        self.assertEqual(VisitaObservacion.objects.get().texto, 'Se visitará el lunes')
        self.ana.refresh_from_db(); self.assertEqual(self.ana.observacion_visita, 'Se visitará el lunes')
        self.assertEqual(mail.outbox[-1].to, ['ana@x.co'])
        self.post('asis_visita_estado', v.id, estado='realizada')
        self.post('asis_visita_estado', v.id, estado='aprobada')  # finalizada: ya no cambia
        v.refresh_from_db(); self.assertEqual(v.estado, 'realizada')
        self.post('asis_visita_nota', v.id, texto='Se entregó el mercado')
        self.assertEqual(v.observaciones.count(), 2, 'una visita finalizada aún admite notas')

    # ── perfil y contraseña ──
    def test_perfil_actualiza_solo_contacto(self):
        self.post('asis_perfil', email='nuevo@x.co', telefono='3150000000', direccion='Dirección nueva 12',
                  nombre='HACK', rol='administrador')
        self.asis.refresh_from_db()
        self.assertEqual((self.asis.email, self.asis.nombre, self.asis.rol), ('nuevo@x.co', 'Ana María', 'asistente'))
        self.post('asis_perfil', email='ana@x.co', telefono='3150000000', direccion='Dirección nueva 12')
        self.asis.refresh_from_db(); self.assertEqual(self.asis.email, 'nuevo@x.co')

    def _codigo_enviado(self):
        self.post('asis_password_enviar')
        return mail.outbox[-1].body.split('\n\n')[2].strip()

    def test_cambio_de_password_con_codigo(self):
        codigo = self._codigo_enviado()
        self.assertTrue(codigo.isdigit() and len(codigo) == 6)
        guardado = json.dumps(dict(self.client.session['pw_codigo']))
        self.assertFalse(codigo in guardado, 'el código no se guarda en claro')
        self.post('asis_password_confirmar', codigo=codigo, password='Nuevita456*', password_confirmation='Nuevita456*')
        self.asis.refresh_from_db(); self.assertTrue(self.asis.check_password('Nuevita456*'))
        self.assertEqual(self.client.get(reverse('dashboard_asistente')).status_code, 200, 'la sesión sigue abierta')
        self.assertNotIn('pw_codigo', self.client.session)
        # un código usado no sirve de nuevo
        self.post('asis_password_confirmar', codigo=codigo, password='Otra98765*', password_confirmation='Otra98765*')
        self.asis.refresh_from_db(); self.assertTrue(self.asis.check_password('Nuevita456*'))

    def test_codigo_incorrecto_limite_de_intentos_y_expiracion(self):
        codigo = self._codigo_enviado()
        malo = '000000' if codigo != '000000' else '111111'
        datos = dict(password='Nuevita456*', password_confirmation='Nuevita456*')
        for _ in range(5):
            self.post('asis_password_confirmar', codigo=malo, **datos)
        # con 5 intentos fallidos, ni el código correcto funciona: hay que pedir otro
        self.post('asis_password_confirmar', codigo=codigo, **datos)
        self.asis.refresh_from_db(); self.assertTrue(self.asis.check_password('Clave123*'))
        # expirado
        codigo = self._codigo_enviado()
        sesion = self.client.session; sesion['pw_codigo']['expira'] = time.time() - 1; sesion.save()
        self.post('asis_password_confirmar', codigo=codigo, **datos)
        self.asis.refresh_from_db(); self.assertTrue(self.asis.check_password('Clave123*'))
        # sin código solicitado
        self.post('asis_password_confirmar', codigo='123456', **datos)
        self.asis.refresh_from_db(); self.assertTrue(self.asis.check_password('Clave123*'))

    def test_password_debil_o_distinta_no_se_acepta(self):
        codigo = self._codigo_enviado()
        self.post('asis_password_confirmar', codigo=codigo, password='123456', password_confirmation='123456')
        self.post('asis_password_confirmar', codigo=codigo, password='Nuevita456*', password_confirmation='otra')
        self.asis.refresh_from_db(); self.assertTrue(self.asis.check_password('Clave123*'))

    def test_si_falla_el_correo_no_queda_codigo_pendiente(self):
        with mock.patch('core.notificaciones.EmailMultiAlternatives.send', side_effect=OSError('smtp caído')):
            self.post('asis_password_enviar')
        self.assertNotIn('pw_codigo', self.client.session)
