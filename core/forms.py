import re
from datetime import date

from django import forms
from django.contrib.auth.forms import PasswordResetForm
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

from .models import TIPOS_DOCUMENTO, Usuario, calcular_edad

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
