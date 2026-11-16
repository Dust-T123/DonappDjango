import re
from datetime import date

from django import forms
from django.contrib.auth.forms import PasswordResetForm
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

from .models import CAMPOS_CORRECCION, TIPOS_DOCUMENTO, Categoria, Usuario, calcular_edad

SOLO_LETRAS = re.compile(r'^[A-Za-záéíóúÁÉÍÓÚüÜñÑ\s]+$')
DOCUMENTO = re.compile(r'^[A-Za-z0-9]{4,15}$')


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
        error_messages={'required': 'El número de documento es obligatorio.'},
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
        error_messages={'required': 'El teléfono es obligatorio.'},
    )
    password = forms.CharField(
        min_length=6, max_length=30,
        error_messages={'required': 'La contraseña es obligatoria.',
                        'min_length': 'La contraseña debe tener al menos 6 caracteres.'},
    )
    password_confirmation = forms.CharField(
        error_messages={'required': 'Debes repetir la contraseña.'},
    )
    # La columna usuario.necesidad es varchar(255).
    necesidad = forms.CharField(max_length=255, required=False)
    aceptaTerminos = forms.BooleanField(
        error_messages={'required': 'Debes aceptar los Términos y Condiciones.'},
    )

    def clean_nombre(self):
        nombre = self.cleaned_data['nombre'].strip()
        if not SOLO_LETRAS.match(nombre):
            raise ValidationError('El nombre solo puede contener letras y espacios.')
        return nombre

    def clean_apellido(self):
        apellido = self.cleaned_data['apellido'].strip()
        if not SOLO_LETRAS.match(apellido):
            raise ValidationError('El apellido solo puede contener letras y espacios.')
        return apellido

    def clean_numDocumento(self):
        numero = self.cleaned_data['numDocumento'].strip()
        if not DOCUMENTO.match(numero):
            raise ValidationError('El número de documento no es válido.')
        if Usuario.objects.filter(num_documento=numero).exists():
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
    password_actual = forms.CharField(required=False)
    password = forms.CharField(required=False)
    password_confirmation = forms.CharField(required=False)

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
