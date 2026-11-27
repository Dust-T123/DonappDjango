"""Sesiones, roles y coherencia de los límites entre módulos."""
import re
import time
from datetime import date
from html.parser import HTMLParser
from pathlib import Path

from django.core.cache import cache
from django.template.loader import render_to_string
from django.test import RequestFactory, TestCase
from django.urls import reverse

from .forms import CLAVE_MAX, CLAVE_MIN, DonappSetPasswordForm
from .models import Categoria, CorreccionDatos, Donacion, DonacionUsuario, Solicitud, Usuario, VisitaDomiciliaria

CLAVE = 'Clave-Segura-9'
PLANTILLAS = Path(__file__).resolve().parent / 'templates' / 'core'


def crear(email, rol='donante', **extra):
    datos = dict(nombre='Ana María', apellido='Pérez', tipo_documento='CC', num_documento=email.split('@')[0],
                 fecha_nacimiento=date(1990, 1, 1), direccion='Calle 1 # 2-3', telefono='3001234567', estado='activo')
    datos.update(extra)
    return Usuario.objects.create_user(email=email, password=CLAVE, rol=rol, **datos)


class RolesYSesionesTests(TestCase):
    def setUp(self):
        cache.clear()
        self.admin = crear('1001@c.co', 'administrador')
        self.asis = crear('1002@c.co', 'asistente')
        self.ana = crear('1003@c.co')

    def test_rol_equivocado_no_muestra_nada_del_modulo_ajeno(self):
        self.client.force_login(self.admin)
        r = self.client.get(reverse('dashboard_usuario'))
        self.assertEqual(r.status_code, 403)
        self.assertTemplateUsed(r, 'core/acceso_denegado.html')
        self.assertNotContains(r, 'modalNuevaDonacion', status_code=403)
        self.assertContains(r, reverse('dashboard_administrador'), status_code=403)   # botón «Ir a mi panel»

    def test_todos_los_cruces_de_rol_son_403(self):
        casos = ((self.ana, 'dashboard_administrador'), (self.ana, 'dashboard_asistente'),
                 (self.asis, 'dashboard_administrador'), (self.asis, 'dashboard_usuario'),
                 (self.admin, 'dashboard_asistente'), (self.admin, 'dashboard_usuario'))
        for quien, nombre in casos:
            self.client.force_login(quien)
            self.assertEqual(self.client.get(reverse(nombre)).status_code, 403, f'{quien.rol} -> {nombre}')

    def test_sin_sesion_va_al_login(self):
        self.assertRedirects(self.client.get(reverse('dashboard_usuario')), reverse('login'))

    def test_las_paginas_con_sesion_no_se_guardan_en_cache(self):
        self.client.force_login(self.ana)
        self.assertIn('no-store', self.client.get(reverse('dashboard_usuario'))['Cache-Control'])
        # y después de cerrar sesión, «Atrás» no puede reutilizar el panel guardado
        r = self.client.post(reverse('logout'))
        self.assertEqual(r.status_code, 302)
        self.assertRedirects(self.client.get(reverse('dashboard_usuario')), reverse('login'))

    def test_la_sesion_se_cierra_por_inactividad(self):
        self.client.force_login(self.ana)
        self.assertEqual(self.client.get(reverse('dashboard_usuario')).status_code, 200)
        sesion = self.client.session
        sesion['ultima_actividad'] = time.time() - 3600
        sesion.save()
        self.assertRedirects(self.client.get(reverse('dashboard_usuario')), reverse('login'))
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_actividad_reciente_mantiene_la_sesion(self):
        self.client.force_login(self.ana)
        self.client.get(reverse('dashboard_usuario'))
        self.assertEqual(self.client.get(reverse('dashboard_usuario')).status_code, 200)

    def test_cambio_de_rol_aplica_en_la_siguiente_peticion(self):
        self.client.force_login(self.asis)
        self.assertEqual(self.client.get(reverse('dashboard_asistente')).status_code, 200)
        self.asis.rol = 'donante'
        self.asis.save()
        self.assertEqual(self.client.get(reverse('dashboard_asistente')).status_code, 403)

    def test_bloqueo_tras_cinco_intentos_fallidos(self):
        for _ in range(5):
            self.client.post(reverse('login'), {'email': self.ana.email, 'contrasena': 'incorrecta'})
        r = self.client.post(reverse('login'), {'email': self.ana.email, 'contrasena': CLAVE}, follow=True)
        self.assertNotIn('_auth_user_id', self.client.session)
        self.assertContains(r, 'Demasiados intentos')

    def test_login_correcto_reinicia_el_contador(self):
        for _ in range(3):
            self.client.post(reverse('login'), {'email': self.ana.email, 'contrasena': 'incorrecta'})
        self.client.post(reverse('login'), {'email': self.ana.email, 'contrasena': CLAVE})
        self.assertIn('_auth_user_id', self.client.session)


class ContrasenaRestablecidaTests(TestCase):
    def test_mismos_limites_que_registro_y_perfil(self):
        u = crear('2001@c.co')
        largo = 'Aa1!' * 10   # 40 caracteres
        f = DonappSetPasswordForm(u, {'new_password1': largo, 'new_password2': largo})
        self.assertFalse(f.is_valid())
        self.assertIn(str(CLAVE_MAX), ' '.join(f.errors['new_password1']))
        ok = 'Clave-Segura-9'
        self.assertTrue(DonappSetPasswordForm(u, {'new_password1': ok, 'new_password2': ok}).is_valid())
        self.assertEqual((CLAVE_MIN, CLAVE_MAX), (6, 30))


class VisibilidadTests(TestCase):
    def setUp(self):
        cache.clear()
        self.admin = crear('3001@c.co', 'administrador')
        self.asis = crear('3002@c.co', 'asistente')
        self.ana = crear('3003@c.co', necesidad='Cobijas')
        self.cat = Categoria.objects.create(nombre='Hogar')

    def _correccion_rechazada(self, solicitante):
        return CorreccionDatos.objects.create(
            usuario=self.ana, solicitante=solicitante, campo='nombre', valor_anterior='Ana', valor_nuevo='Anita',
            justificacion='Error de digitación en el registro', estado='rechazada',
            observacion_resolucion='El documento adjunto está ilegible', soporte_ruta='x', soporte_mime='image/png',
            soporte_hash='0' * 64, consentimiento=True)

    def test_el_donante_ve_el_motivo_de_rechazo(self):
        self._correccion_rechazada(self.ana)
        self.client.force_login(self.ana)
        r = self.client.get(reverse('dashboard_usuario'))
        self.assertContains(r, 'Motivo del rechazo')
        self.assertContains(r, 'El documento adjunto está ilegible')

    def test_el_asistente_ve_el_motivo_de_rechazo(self):
        self._correccion_rechazada(self.asis)
        self.client.force_login(self.asis)
        self.assertContains(self.client.get(reverse('dashboard_asistente')), 'El documento adjunto está ilegible')

    def test_rechazo_sin_motivo_lo_dice(self):
        c = self._correccion_rechazada(self.ana)
        c.observacion_resolucion = None
        c.save()
        self.client.force_login(self.ana)
        self.assertContains(self.client.get(reverse('dashboard_usuario')), 'no registró un motivo')

    def test_canceladas_se_ven_en_solo_lectura_para_admin_y_asistente(self):
        d = Donacion.objects.create(descripcion='Mesa de comedor', categoria=self.cat, stock=1, estado='cancelada')
        DonacionUsuario.objects.create(donante=self.ana, donacion=d)
        Solicitud.objects.create(descripcion='Cobijas para el invierno', solicitante=self.ana, categoria=self.cat, estado='cancelada')
        for quien, panel in ((self.admin, 'dashboard_administrador'), (self.asis, 'dashboard_asistente')):
            self.client.force_login(quien)
            html = self.client.get(reverse(panel)).content.decode()
            self.assertIn('detalleDonacion(', html)
            self.assertIn('detalleSolicitud(', html)
            # ninguna acción de gestión para fichas canceladas
            self.assertNotIn('abrirModalDonacion(JSON.parse', html)
            self.assertNotIn('abrirModalSolicitud(JSON.parse', html)

    def test_stock_y_visitas_traen_el_texto_completo(self):
        nombre = 'Un celular Motorola azul en buen estado con cargador original y funda'
        Donacion.objects.create(descripcion=nombre, categoria=self.cat, stock=1, estado='aprobada')
        VisitaDomiciliaria.objects.create(usuario=self.ana, direccion='Calle 1 # 2-3', motivo='Verificar necesidad de alimentos para la familia')
        self.client.force_login(self.admin)
        r = self.client.get(reverse('dashboard_administrador'))
        html = r.content.decode()
        self.assertIn('detalleStock(', html)
        self.assertIn(nombre, html)
        self.assertIn('Verificar necesidad de alimentos para la familia', r.context['visitas'][0].json)
        self.assertIn('gestion_detalle.js', html)
        self.assertIn('modalDetalleGeneral', html)

    def test_modal_de_crear_usuario_pide_el_rol_primero(self):
        self.client.force_login(self.admin)
        html = self.client.get(reverse('dashboard_administrador')).content.decode()
        modal = html[html.index('id="modalCrearUsuario"'):]
        modal = modal[:modal.index('</form>')]
        self.assertLess(modal.index('name="rol"'), modal.index('name="nombre"'))
        self.assertLess(modal.index('name="rol"'), modal.index('name="necesidad"'))
        self.assertIn('grp_nuevo_nec', modal)
        self.assertIn('grp_nuevo_prioridad', modal)


class CorreoYTerminosTests(TestCase):
    def test_boton_del_correo_tiene_texto_blanco_sobre_azul(self):
        html = render_to_string('core/emails/recuperacion_contrasena.html', {
            'user': Usuario(nombre='Ana'), 'protocol': 'http', 'domain': 'x.co', 'uid': 'MQ', 'token': 'abc-123'})
        self.assertIn('bgcolor="#0B5AA6"', html)
        self.assertRegex(html, r'color:#ffffff !important')
        self.assertIn('Restablecer contraseña', html)

    def test_barra_de_terminos_conoce_los_destinos(self):
        html = self.client.get(reverse('terminos')).content.decode()
        self.assertIn('data-autenticado="0"', html)
        self.assertIn(f'data-registro="{reverse("registro")}"', html)
        self.assertIn(f'data-login="{reverse("login")}"', html)

    def test_con_sesion_la_barra_lleva_al_panel(self):
        ana = crear('4001@c.co')
        self.client.force_login(ana)
        html = self.client.get(reverse('terminos')).content.decode()
        self.assertIn('data-autenticado="1"', html)
        self.assertIn(f'data-panel="{reverse("dashboard_usuario")}"', html)


# ── Los mismos campos, los mismos límites en todos los módulos ─────────────────────────
LIMITES_HTML = {
    'nombre': 100, 'apellido': 100, 'direccion': 255, 'email': 150, 'necesidad': 255, 'telefono': 10,
    'numDocumento': 15, 'password': 30, 'password_confirmation': 30, 'new_password1': 30, 'new_password2': 30,
    'nombre_categoria': 100, 'observacion_visita': 500, 'justificacion': 300, 'valorNuevo': 150, 'texto': 500,
    'codigo': 6,
}


class _Campos(HTMLParser):
    def __init__(self):
        super().__init__()
        self.campos = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag in ('input', 'textarea') and a.get('name') in LIMITES_HTML and 'maxlength' in a:
            self.campos.append((a['name'], a['maxlength']))


class LimitesCompartidosTests(TestCase):
    def test_ningun_template_se_aparta_del_limite_del_servidor(self):
        errores = []
        for ruta in sorted(PLANTILLAS.glob('*.html')):
            texto = re.sub(r'\{%.*?%\}|\{\{.*?\}\}', 'X', ruta.read_text(encoding='utf-8'), flags=re.S)
            parser = _Campos()
            parser.feed(texto)
            for nombre, maximo in parser.campos:
                if not maximo.isdigit() or int(maximo) != LIMITES_HTML[nombre]:
                    errores.append(f'{ruta.name}: {nombre} maxlength={maximo} (esperado {LIMITES_HTML[nombre]})')
        self.assertEqual(errores, [])

    def test_los_formularios_del_servidor_usan_los_mismos_maximos(self):
        from . import forms
        for formulario, campo, maximo in (
            (forms.RegistroForm, 'nombre', 100), (forms.RegistroForm, 'apellido', 100),
            (forms.RegistroForm, 'direccion', 255), (forms.RegistroForm, 'email', 150), (forms.RegistroForm, 'necesidad', 255),
            (forms.PerfilDonanteForm, 'direccion', 255), (forms.PerfilDonanteForm, 'necesidad', 255),
            (forms.DonanteEditarForm, 'direccion', 255), (forms.DonanteEditarForm, 'necesidad', 255),
            (forms.PerfilPersonalForm, 'direccion', 255), (forms.UsuarioAdminCrearForm, 'necesidad', 255),
            (forms.UsuarioAdminEditarForm, 'necesidad', 255),
        ):
            self.assertEqual(formulario.base_fields[campo].max_length, maximo, f'{formulario.__name__}.{campo}')
