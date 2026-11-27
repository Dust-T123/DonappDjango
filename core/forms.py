import re
from datetime import date, datetime

from django import forms
from django.contrib.auth.forms import PasswordResetForm, SetPasswordForm
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.utils.dateparse import parse_date

from .models import (
    CAMPOS_CORRECCION, ESTADOS_DONACION, ESTADOS_EVENTO, TIPOS_DOCUMENTO, Categoria, Usuario, calcular_edad,
)

SOLO_LETRAS = re.compile(r'^[A-Za-záéíóúÁÉÍÓÚüÜñÑ\s]+$')
# Reglas del número según el tipo de documento (como en la vida real):
#   CC, TI, CE, TE y PPT son numéricos; solo el pasaporte mezcla letras y números.
DOCUMENTO_NUMERICO = re.compile(r'^[0-9]{4,15}$')
DOCUMENTO_ALFANUMERICO = re.compile(r'^[A-Za-z0-9]{4,15}$')
TIPOS_CON_LETRAS = ('Pasaporte',)
MSG_DOCUMENTO_NUMERICO = ('El número de documento debe tener entre 4 y 15 dígitos y solo puede '
                          'contener números (para {tipo} no se permiten letras).')
MSG_DOCUMENTO_ALFANUMERICO = ('El número de pasaporte debe tener entre 4 y 15 caracteres y solo puede '
                              'contener letras y números (sin espacios ni símbolos).')
MSG_DOCUMENTO = ('El número de documento debe tener entre 4 y 15 caracteres y solo puede '
                 'contener letras y números (sin espacios ni símbolos).')
# Límites comunes a los tres paneles (registro, perfil, altas y ediciones del personal).
CLAVE_MIN, CLAVE_MAX = 6, 30
MSG_CLAVE_MAX = f'La contraseña no puede superar {CLAVE_MAX} caracteres.'
OBSERVACION_ESTADO_MAX = 200   # donacion.observacion es varchar(200)


def normalizar_documento(valor):
    """Quita espacios y deja el documento en mayúsculas (así 'ab123' y 'AB123' son el mismo)."""
    return (valor or '').strip().upper()


def validar_numero_documento(tipo, numero):
    """Mensaje de error si `numero` no es válido para el tipo de documento; None si lo es."""
    if tipo in TIPOS_CON_LETRAS:
        return None if DOCUMENTO_ALFANUMERICO.match(numero) else MSG_DOCUMENTO_ALFANUMERICO
    if tipo in dict(TIPOS_DOCUMENTO):
        return None if DOCUMENTO_NUMERICO.match(numero) else MSG_DOCUMENTO_NUMERICO.format(tipo=tipo)
    return None if DOCUMENTO_ALFANUMERICO.match(numero) else MSG_DOCUMENTO


def validar_valor_correccion(campo, valor, usuario=None):
    """Valida el valor propuesto en una corrección de datos según el campo.

    Devuelve (valor_normalizado, None) o (None, mensaje). No consulta la base de datos
    (la unicidad del documento la revisa quien aprueba). Con `usuario`, el número de documento
    se valida contra el tipo de documento que ese usuario tiene hoy.
    """
    valor = (valor or '').strip()
    if campo == 'numDocumento':
        valor = normalizar_documento(valor)
        error = validar_numero_documento(getattr(usuario, 'tipo_documento', None), valor)
        if error:
            return None, 'El número de documento propuesto no es válido. ' + error
        return valor, None
    if campo == 'tipoDocumento':
        if valor not in dict(TIPOS_DOCUMENTO):
            return None, 'Tipo de documento propuesto no es válido.'
        return valor, None
    if campo == 'fechaNacimiento':
        fecha = None
        try:
            fecha = parse_date(valor)
        except ValueError:
            fecha = None
        if fecha is None:
            try:
                fecha = datetime.strptime(valor, '%d/%m/%Y').date()
            except ValueError:
                return None, 'La fecha de nacimiento propuesta no es válida (usa AAAA-MM-DD).'
        if fecha > date.today() or calcular_edad(fecha) < 14:
            return None, ('La fecha de nacimiento propuesta indica una edad menor a 14 años, '
                          'no permitida en la plataforma.')
        return fecha, None
    if campo in ('nombre', 'apellido'):
        minimo = 3 if campo == 'nombre' else 2
        valor = ' '.join(valor.split())
        if not minimo <= len(valor) <= 100:
            return None, f'El {campo} propuesto debe tener entre {minimo} y 100 caracteres.'
        if not SOLO_LETRAS.match(valor):
            return None, f'El {campo} propuesto solo puede contener letras y espacios.'
        return valor, None
    return valor, None


class RegistroForm(forms.Form):
    """Registro público de donantes. Los nombres de los campos coinciden con los
    del formulario original (tipoDocumento, numDocumento, fechaNacimiento...)
    para que registro.js funcione sin cambios."""

    nombre = forms.CharField(
        min_length=3, max_length=100,
        error_messages={'required': 'El nombre es obligatorio.',
                        'min_length': 'El nombre debe tener al menos 3 caracteres.'},
    )
    apellido = forms.CharField(
        min_length=2, max_length=100,
        error_messages={'required': 'El apellido es obligatorio.',
                        'min_length': 'El apellido debe tener al menos 2 caracteres.'},
    )
    tipoDocumento = forms.ChoiceField(
        choices=TIPOS_DOCUMENTO,
        error_messages={'required': 'Selecciona el tipo de documento.',
                        'invalid_choice': 'El tipo de documento no es válido.'},
    )
    numDocumento = forms.CharField(
        max_length=15,
        error_messages={'required': 'El número de documento es obligatorio.',
                        'max_length': 'El número de documento no puede superar 15 caracteres.'},
    )
    fechaNacimiento = forms.DateField(
        error_messages={'required': 'La fecha de nacimiento es obligatoria.',
                        'invalid': 'La fecha de nacimiento no es válida.'},
    )
    direccion = forms.CharField(
        min_length=5, max_length=255,
        error_messages={'required': 'La dirección es obligatoria.',
                        'min_length': 'La dirección debe tener al menos 5 caracteres.'},
    )
    email = forms.EmailField(
        max_length=150,
        error_messages={'required': 'El correo es obligatorio.',
                        'invalid': 'Escribe un correo electrónico válido.'},
    )
    telefono = forms.CharField(
        max_length=10,
        error_messages={'required': 'El teléfono es obligatorio.',
                        'max_length': 'El teléfono debe tener exactamente 10 dígitos.'},
    )
    password = forms.CharField(
        min_length=CLAVE_MIN, max_length=CLAVE_MAX,
        error_messages={'required': 'La contraseña es obligatoria.',
                        'min_length': 'La contraseña debe tener al menos 6 caracteres.',
                        'max_length': MSG_CLAVE_MAX},
    )
    password_confirmation = forms.CharField(
        max_length=CLAVE_MAX,
        error_messages={'required': 'Debes repetir la contraseña.', 'max_length': MSG_CLAVE_MAX},
    )
    # La columna usuario.necesidad es varchar(255).
    necesidad = forms.CharField(max_length=255, required=False)
    aceptaTerminos = forms.BooleanField(
        error_messages={'required': 'Debes aceptar los Términos y Condiciones.'},
    )

    def clean_nombre(self):
        nombre = ' '.join(self.cleaned_data['nombre'].split())
        if not SOLO_LETRAS.match(nombre):
            raise ValidationError('El nombre solo puede contener letras y espacios.')
        return nombre

    def clean_apellido(self):
        apellido = ' '.join(self.cleaned_data['apellido'].split())
        if not SOLO_LETRAS.match(apellido):
            raise ValidationError('El apellido solo puede contener letras y espacios.')
        return apellido

    def clean_numDocumento(self):
        numero = normalizar_documento(self.cleaned_data['numDocumento'])
        # tipoDocumento se declara antes, así que ya está limpio aquí (si fue inválido, falta).
        error = validar_numero_documento(self.cleaned_data.get('tipoDocumento'), numero)
        if error:
            raise ValidationError(error)
        if Usuario.objects.filter(num_documento__iexact=numero).exists():
            raise ValidationError('Este número de documento ya está registrado.')
        return numero

    def clean_fechaNacimiento(self):
        fecha = self.cleaned_data['fechaNacimiento']
        if fecha > date.today() or calcular_edad(fecha) < 14:
            raise ValidationError('Debes tener al menos 14 años para registrarte en Donapp.')
        return fecha

    def clean_email(self):
        correo = self.cleaned_data['email'].strip().lower()
        if Usuario.objects.filter(email__iexact=correo).exists():
            raise ValidationError('Este correo ya está registrado.')
        return correo

    def clean_telefono(self):
        telefono = self.cleaned_data['telefono'].strip()
        if not re.fullmatch(r'\d{10}', telefono):
            raise ValidationError('El teléfono debe tener exactamente 10 dígitos.')
        return telefono

    def clean(self):
        datos = super().clean()
        clave = datos.get('password')
        if clave:
            if clave != datos.get('password_confirmation'):
                self.add_error('password_confirmation', 'Las contraseñas no coinciden.')
            else:
                try:
                    validate_password(clave)
                except ValidationError as error:
                    self.add_error('password', error)
        return datos


class DonappSetPasswordForm(SetPasswordForm):
    """Restablecer contraseña (enlace del correo) con los mismos límites que registro y perfil:
    entre CLAVE_MIN y CLAVE_MAX caracteres."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for campo in ('new_password1', 'new_password2'):
            self.fields[campo].max_length = CLAVE_MAX
            self.fields[campo].min_length = CLAVE_MIN
            self.fields[campo].widget.attrs.update({'maxlength': CLAVE_MAX, 'minlength': CLAVE_MIN})

    def clean_new_password1(self):
        clave = self.cleaned_data.get('new_password1') or ''
        if len(clave) > CLAVE_MAX:
            raise ValidationError(MSG_CLAVE_MAX)
        return clave


class DonappPasswordResetForm(PasswordResetForm):
    """Igual que el original de Django, pero 'activo' es el campo `estado`
    (en este modelo is_active es una propiedad, no una columna)."""

    def get_users(self, email):
        usuarios = Usuario.objects.filter(email__iexact=email, estado='activo')
        return (u for u in usuarios if u.has_usable_password())


# ── FORMULARIOS DEL PANEL DEL DONANTE ────────────────────────────────────────
# Los nombres de campo (idCategoria, fechaPreferida, valorNuevo...) son los mismos
# del Blade original, así los templates y el JS no cambian.

class DonacionForm(forms.Form):
    descripcion = forms.CharField(
        min_length=5, max_length=200,
        error_messages={'required': 'La descripción es obligatoria.',
                        'min_length': 'La descripción debe tener al menos 5 caracteres.'},
    )
    idCategoria = forms.ModelChoiceField(
        queryset=Categoria.objects.all(),
        error_messages={'required': 'Selecciona una categoría.',
                        'invalid_choice': 'La categoría no existe.'},
    )
    stock = forms.IntegerField(
        min_value=1, max_value=9999,
        error_messages={'required': 'La cantidad es obligatoria.',
                        'min_value': 'La cantidad mínima es 1.',
                        'max_value': 'La cantidad máxima es 9999.'},
    )
    # ImageField verifica con Pillow que el archivo sea realmente una imagen.
    imagen = forms.ImageField(required=False, error_messages={'invalid_image': 'La imagen no es válida.'})


class SolicitudForm(forms.Form):
    descripcion = forms.CharField(
        min_length=5, max_length=300,
        error_messages={'required': 'La descripción es obligatoria.',
                        'min_length': 'La descripción debe tener al menos 5 caracteres.'},
    )
    idCategoria = forms.ModelChoiceField(
        queryset=Categoria.objects.all(),
        error_messages={'required': 'Selecciona una categoría.',
                        'invalid_choice': 'La categoría no existe.'},
    )


class VisitaForm(forms.Form):
    direccion = forms.CharField(min_length=5, max_length=255,
                                error_messages={'required': 'La dirección es obligatoria.',
                                                'min_length': 'La dirección debe tener al menos 5 caracteres.'})
    motivo = forms.CharField(min_length=10, max_length=300,
                             error_messages={'required': 'El motivo es obligatorio.',
                                             'min_length': 'El motivo debe tener al menos 10 caracteres.'})
    fechaPreferida = forms.DateField(required=False, error_messages={'invalid': 'La fecha preferida no es válida.'})

    def clean_fechaPreferida(self):
        fecha = self.cleaned_data.get('fechaPreferida')
        if fecha and fecha < date.today():
            raise ValidationError('La fecha preferida no puede ser anterior a hoy.')
        return fecha


class NotaVisitaForm(forms.Form):
    texto = forms.CharField(min_length=3, max_length=500,
                            error_messages={'required': 'Escribe la nota.',
                                            'min_length': 'La nota debe tener al menos 3 caracteres.'})


class PerfilDonanteForm(forms.Form):
    """Solo campos NO sensibles. Nombre, documento y fecha de nacimiento se
    cambian únicamente por el flujo de corrección (habeas data)."""

    email = forms.EmailField(max_length=150, error_messages={'required': 'El correo es obligatorio.',
                                                               'invalid': 'Escribe un correo electrónico válido.'})
    telefono = forms.RegexField(regex=r'^\d{10}$', error_messages={'required': 'El teléfono es obligatorio.',
                                                                    'invalid': 'El teléfono debe tener 10 dígitos.'})
    direccion = forms.CharField(min_length=5, max_length=255,
                                error_messages={'required': 'La dirección es obligatoria.',
                                                'min_length': 'La dirección debe tener al menos 5 caracteres.'})
    necesidad = forms.CharField(required=False, max_length=255)
    password_actual = forms.CharField(required=False, max_length=128)
    password = forms.CharField(required=False, max_length=CLAVE_MAX, error_messages={'max_length': MSG_CLAVE_MAX})
    password_confirmation = forms.CharField(required=False, max_length=CLAVE_MAX,
                                            error_messages={'max_length': MSG_CLAVE_MAX})

    def __init__(self, *args, usuario, **kwargs):
        super().__init__(*args, **kwargs)
        self.usuario = usuario

    def clean_email(self):
        email = self.cleaned_data['email']
        if Usuario.objects.filter(email__iexact=email).exclude(pk=self.usuario.pk).exists():
            raise ValidationError('Ese correo ya está registrado por otra cuenta.')
        return email

    def clean(self):
        datos = super().clean()
        nueva = datos.get('password')
        if nueva:
            if not self.usuario.check_password(datos.get('password_actual', '')):
                self.add_error('password_actual', 'La contraseña actual es incorrecta.')
            elif nueva != datos.get('password_confirmation'):
                self.add_error('password', 'Las contraseñas no coinciden.')
            else:
                try:
                    validate_password(nueva, self.usuario)
                except ValidationError as e:
                    self.add_error('password', e)
        return datos


EXTENSIONES_SOPORTE = {'jpg', 'jpeg', 'png', 'pdf'}
FIRMAS_SOPORTE = (b'\xff\xd8\xff', b'\x89PNG\r\n\x1a\n', b'%PDF-')  # JPEG, PNG, PDF
TAMANO_MAX_SOPORTE = 4 * 1024 * 1024


class CorreccionForm(forms.Form):
    campo = forms.ChoiceField(choices=CAMPOS_CORRECCION,
                              error_messages={'required': 'Selecciona el campo a corregir.',
                                              'invalid_choice': 'El campo seleccionado no es válido.'})
    valorNuevo = forms.CharField(max_length=150, error_messages={'required': 'Escribe el valor correcto propuesto.'})
    justificacion = forms.CharField(min_length=10, max_length=300,
                                    error_messages={'required': 'La justificación es obligatoria.',
                                                    'min_length': 'La justificación debe tener al menos 10 caracteres.'})
    soporte = forms.FileField(error_messages={'required': 'Adjunta el documento de identidad.'})
    consentimiento = forms.BooleanField(error_messages={'required': 'Debes autorizar el tratamiento del documento.'})

    def __init__(self, *args, usuario=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.usuario = usuario   # a quién se le corrige el dato (define el tipo de documento vigente)

    def clean(self):
        datos = super().clean()
        campo, valor = datos.get('campo'), datos.get('valorNuevo')
        if campo and valor:
            _, error = validar_valor_correccion(campo, valor, self.usuario)
            if error:
                self.add_error('valorNuevo', error)
        return datos

    def clean_soporte(self):
        archivo = self.cleaned_data['soporte']
        extension = archivo.name.rsplit('.', 1)[-1].lower() if '.' in archivo.name else ''
        if extension not in EXTENSIONES_SOPORTE:
            raise ValidationError('El soporte debe ser JPG, PNG o PDF.')
        if archivo.size > TAMANO_MAX_SOPORTE:
            raise ValidationError('El soporte no puede superar 4 MB.')
        # No se confía en la extensión ni en el Content-Type: se revisa la firma real del archivo.
        cabecera = archivo.read(8)
        archivo.seek(0)
        if not cabecera.startswith(FIRMAS_SOPORTE):
            raise ValidationError('El contenido del archivo no corresponde a una imagen JPG/PNG o a un PDF.')
        return archivo


# ── FORMULARIOS COMPARTIDOS ASISTENTE / ADMINISTRADOR ────────────────────────

SOLO_CATEGORIA = re.compile(r'^[A-Za-záéíóúÁÉÍÓÚñÑüÜ\s()\-,:.]+$')
PRIORIDADES_VALIDAS = [(v, v) for v in ('urgente', 'alta', 'media', 'baja')]


class CategoriaForm(forms.Form):
    # El campo se llama nombre_categoria como en el Blade original.
    nombre_categoria = forms.CharField(
        min_length=3, max_length=100,
        error_messages={'required': 'El nombre de la categoría es obligatorio.',
                        'min_length': 'El nombre debe tener al menos 3 caracteres.'},
    )

    def __init__(self, *args, excluir_pk=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.excluir_pk = excluir_pk

    def clean_nombre_categoria(self):
        nombre = ' '.join(self.cleaned_data['nombre_categoria'].split())
        if not SOLO_CATEGORIA.match(nombre):
            raise ValidationError('El nombre de una categoría solo puede contener letras, espacios, '
                                  'guiones, paréntesis, comas, puntos y dos puntos (nunca números).')
        if Categoria.objects.filter(nombre__iexact=nombre).exclude(pk=self.excluir_pk).exists():
            raise ValidationError('Ya existe una categoría con ese nombre.')
        return nombre


class EventoForm(forms.Form):
    nombre_evento = forms.CharField(min_length=3, max_length=150,
                                    error_messages={'required': 'El nombre del evento es obligatorio.',
                                                    'min_length': 'El nombre del evento debe tener al menos 3 caracteres.'})
    fecha_inicio = forms.DateField(error_messages={'required': 'La fecha de inicio es obligatoria.',
                                                   'invalid': 'La fecha de inicio no es válida.'})
    fecha_fin = forms.DateField(error_messages={'required': 'La fecha de fin es obligatoria.',
                                                'invalid': 'La fecha de fin no es válida.'})
    lugar_entrega = forms.CharField(min_length=3, max_length=255,
                                    error_messages={'required': 'El lugar de entrega es obligatorio.',
                                                    'min_length': 'El lugar debe tener al menos 3 caracteres.'})
    # Se guarda en evento.nombre (varchar 150): con 200 el servidor fallaba al guardar.
    titulo_pub = forms.CharField(min_length=3, max_length=150,
                                 error_messages={'required': 'El título de la publicación es obligatorio.',
                                                 'min_length': 'El título debe tener al menos 3 caracteres.',
                                                 'max_length': 'El título no puede superar 150 caracteres.'})
    contenido_pub = forms.CharField(min_length=10, max_length=500,
                                    error_messages={'required': 'El contenido es obligatorio.',
                                                    'min_length': 'El contenido debe tener al menos 10 caracteres.'})
    estado_evento = forms.ChoiceField(choices=ESTADOS_EVENTO, required=False,
                                      error_messages={'invalid_choice': 'El estado del evento no es válido.'})
    imagen_pub = forms.ImageField(required=False, error_messages={'invalid_image': 'La imagen no es válida.'})

    def __init__(self, *args, nuevo=True, **kwargs):
        super().__init__(*args, **kwargs)
        # Al crear no se aceptan fechas pasadas; al editar sí (un evento ya iniciado se puede corregir).
        self.nuevo = nuevo

    def clean(self):
        datos = super().clean()
        inicio, fin = datos.get('fecha_inicio'), datos.get('fecha_fin')
        if self.nuevo:
            if inicio and inicio < date.today():
                self.add_error('fecha_inicio', 'No se pueden crear eventos con fechas pasadas. '
                                               'Selecciona hoy o una fecha futura.')
            elif fin and fin < date.today():
                self.add_error('fecha_fin', 'La fecha de fin debe ser hoy o una fecha futura, '
                                            'y no puede ser anterior a la de inicio.')
        if inicio and fin and fin < inicio and 'fecha_fin' not in self.errors:
            self.add_error('fecha_fin', 'La fecha de fin no puede ser anterior a la de inicio.')
        return datos


class EstadoEventoForm(forms.Form):
    estado = forms.ChoiceField(choices=ESTADOS_EVENTO, error_messages={'required': 'Selecciona un estado.',
                                                                         'invalid_choice': 'El estado no es válido.'})


class EstadoGestionForm(forms.Form):
    """Cambio de estado de una donación o solicitud, con observación opcional."""
    estado = forms.ChoiceField(choices=ESTADOS_DONACION, error_messages={'required': 'Selecciona un estado.',
                                                                           'invalid_choice': 'El estado no es válido.'})
    # donacion.observacion es varchar(200): con 250 el guardado fallaba (error 500).
    observacion = forms.CharField(required=False, max_length=OBSERVACION_ESTADO_MAX,
                                  error_messages={'max_length': f'La observación no puede superar {OBSERVACION_ESTADO_MAX} caracteres.'})

    def clean(self):
        datos = super().clean()
        # Regla que el JS ya exigía en pantalla; ahora también en el servidor.
        if datos.get('estado') == 'rechazada' and not (datos.get('observacion') or '').strip():
            self.add_error('observacion', 'La observación es obligatoria al rechazar.')
        return datos


class EstadoVisitaForm(forms.Form):
    estado = forms.ChoiceField(choices=[(v, v) for v in ('aprobada', 'rechazada', 'realizada', 'cancelada')],
                               error_messages={'required': 'Selecciona un estado.',
                                               'invalid_choice': 'El estado no es válido.'})
    observacion = forms.CharField(required=False, max_length=500)


class DonanteCrearForm(RegistroForm):
    """Alta de un donante/solicitante hecha por el personal (no acepta términos: es presencial)."""
    aceptaTerminos = None
    prioridad = forms.ChoiceField(choices=PRIORIDADES_VALIDAS, required=False,
                                  error_messages={'invalid_choice': 'La prioridad no es válida.'})
    observacion_visita = forms.CharField(required=False, max_length=500)

    def clean_fechaNacimiento(self):
        fecha = self.cleaned_data['fechaNacimiento']
        if fecha > date.today() or calcular_edad(fecha) < 14:
            raise ValidationError('El donante/solicitante debe tener al menos 14 años.')
        return fecha


class DonanteEditarForm(forms.Form):
    """Solo campos NO sensibles de un donante (los de identidad van por corrección)."""
    email = forms.EmailField(max_length=150, error_messages={'required': 'El correo es obligatorio.',
                                                               'invalid': 'Escribe un correo electrónico válido.'})
    telefono = forms.RegexField(regex=r'^\d{10}$', error_messages={'required': 'El teléfono es obligatorio.',
                                                                    'invalid': 'El teléfono debe tener 10 dígitos.'})
    direccion = forms.CharField(min_length=5, max_length=255,
                                error_messages={'required': 'La dirección es obligatoria.',
                                                'min_length': 'La dirección debe tener al menos 5 caracteres.'})
    necesidad = forms.CharField(required=False, max_length=255)
    prioridad = forms.ChoiceField(choices=PRIORIDADES_VALIDAS, required=False,
                                  error_messages={'invalid_choice': 'La prioridad no es válida.'})
    observacion_visita = forms.CharField(required=False, max_length=500)
    password = forms.CharField(required=False, max_length=CLAVE_MAX, error_messages={'max_length': MSG_CLAVE_MAX})
    password_confirmation = forms.CharField(required=False, max_length=CLAVE_MAX,
                                            error_messages={'max_length': MSG_CLAVE_MAX})

    def __init__(self, *args, usuario, **kwargs):
        super().__init__(*args, **kwargs)
        self.usuario = usuario

    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()
        if Usuario.objects.filter(email__iexact=email).exclude(pk=self.usuario.pk).exists():
            raise ValidationError('Ese correo ya está registrado por otra cuenta.')
        return email

    def clean(self):
        datos = super().clean()
        clave = datos.get('password')
        if clave:
            if clave != datos.get('password_confirmation'):
                self.add_error('password', 'Las contraseñas no coinciden.')
            else:
                try:
                    validate_password(clave, self.usuario)
                except ValidationError as e:
                    self.add_error('password', e)
        return datos


class PerfilPersonalForm(forms.Form):
    """Perfil propio del personal (asistente/administrador): datos de contacto únicamente."""
    email = forms.EmailField(max_length=150, error_messages={'required': 'El correo es obligatorio.',
                                                               'invalid': 'Escribe un correo electrónico válido.'})
    telefono = forms.RegexField(regex=r'^\d{10}$', error_messages={'required': 'El teléfono es obligatorio.',
                                                                    'invalid': 'El teléfono debe tener 10 dígitos.'})
    direccion = forms.CharField(min_length=5, max_length=255,
                                error_messages={'required': 'La dirección es obligatoria.',
                                                'min_length': 'La dirección debe tener al menos 5 caracteres.'})

    def __init__(self, *args, usuario, **kwargs):
        super().__init__(*args, **kwargs)
        self.usuario = usuario

    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()
        if Usuario.objects.filter(email__iexact=email).exclude(pk=self.usuario.pk).exists():
            raise ValidationError('Ese correo ya está registrado por otra cuenta.')
        return email


class ConfirmarPasswordForm(forms.Form):
    codigo = forms.RegexField(regex=r'^\d{6}$', error_messages={'required': 'Ingresa el código de 6 dígitos.',
                                                                 'invalid': 'El código debe tener 6 dígitos.'})
    password = forms.CharField(max_length=CLAVE_MAX, error_messages={'required': 'La nueva contraseña es obligatoria.',
                                                                    'max_length': MSG_CLAVE_MAX})
    password_confirmation = forms.CharField(max_length=CLAVE_MAX, error_messages={
        'required': 'Debes repetir la contraseña.', 'max_length': MSG_CLAVE_MAX})

    def __init__(self, *args, usuario, **kwargs):
        super().__init__(*args, **kwargs)
        self.usuario = usuario

    def clean(self):
        datos = super().clean()
        clave = datos.get('password')
        if clave:
            if clave != datos.get('password_confirmation'):
                self.add_error('password', 'Las contraseñas no coinciden.')
            else:
                try:
                    validate_password(clave, self.usuario)
                except ValidationError as e:
                    self.add_error('password', e)
        return datos


# ── FORMULARIOS EXCLUSIVOS DEL ADMINISTRADOR ─────────────────────────────────

ROLES_VALIDOS = [(v, v) for v in ('administrador', 'asistente', 'donante')]
ESTADOS_CUENTA = [(v, v) for v in ('activo', 'inactivo')]


class UsuarioAdminCrearForm(DonanteCrearForm):
    """Alta de cualquier usuario (incluido personal). Necesidad/prioridad solo aplican a donantes."""
    rol = forms.ChoiceField(choices=ROLES_VALIDOS, error_messages={'required': 'Selecciona un rol.',
                                                                   'invalid_choice': 'El rol no es válido.'})
    estado = forms.ChoiceField(choices=ESTADOS_CUENTA, error_messages={'required': 'Selecciona un estado.',
                                                                       'invalid_choice': 'El estado no es válido.'})

    def clean_fechaNacimiento(self):
        fecha = self.cleaned_data['fechaNacimiento']
        if fecha > date.today() or calcular_edad(fecha) < 14:
            raise ValidationError('El usuario debe tener al menos 14 años.')
        return fecha


class UsuarioAdminEditarForm(DonanteEditarForm):
    """Edición de un usuario por el administrador: contacto, rol, estado y (si es donante) seguimiento."""
    rol = forms.ChoiceField(choices=ROLES_VALIDOS, error_messages={'required': 'Selecciona un rol.',
                                                                   'invalid_choice': 'El rol no es válido.'})
    estado = forms.ChoiceField(choices=ESTADOS_CUENTA, error_messages={'required': 'Selecciona un estado.',
                                                                       'invalid_choice': 'El estado no es válido.'})


class RechazoCorreccionForm(forms.Form):
    motivo = forms.CharField(required=False, max_length=300,
                             error_messages={'max_length': 'El motivo no puede superar 300 caracteres.'})
