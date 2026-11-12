from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import (
    AdminPasswordChangeForm, BaseUserCreationForm, UserChangeForm,
)

from . import models


class UsuarioCreationForm(BaseUserCreationForm):
    class Meta:
        model = models.Usuario
        fields = ('email', 'nombre', 'apellido', 'tipo_documento', 'num_documento',
                  'fecha_nacimiento', 'direccion', 'telefono', 'rol')


class UsuarioChangeForm(UserChangeForm):
    class Meta:
        model = models.Usuario
        fields = '__all__'


@admin.register(models.Usuario)
class UsuarioAdmin(UserAdmin):
    """Admin de usuarios: la contraseña se cambia con el formulario que la
    cifra (no se edita como texto plano)."""

    form = UsuarioChangeForm
    add_form = UsuarioCreationForm
    change_password_form = AdminPasswordChangeForm
    ordering = ('email',)
    list_display = ('email', 'nombre', 'apellido', 'rol', 'estado')
    list_filter = ('rol', 'estado')
    search_fields = ('email', 'nombre', 'apellido', 'num_documento')
    filter_horizontal = ('groups', 'user_permissions')

    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Datos personales', {'fields': (
            'nombre', 'apellido', 'tipo_documento', 'num_documento',
            'fecha_nacimiento', 'direccion', 'telefono',
        )}),
        ('Apoyo solicitado (solo donantes)', {'fields': (
            'necesidad', 'prioridad', 'observacion_visita',
        )}),
        ('Acceso', {'fields': ('rol', 'estado', 'is_superuser', 'groups', 'user_permissions')}),
        ('Fechas', {'fields': ('last_login',)}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': (
                'email', 'nombre', 'apellido', 'tipo_documento', 'num_documento',
                'fecha_nacimiento', 'direccion', 'telefono', 'rol',
                'password1', 'password2',
            ),
        }),
    )


for modelo in (
    models.Categoria,
    models.Evento,
    models.Donacion,
    models.Solicitud,
    models.DonacionUsuario,
    models.VisitaDomiciliaria,
    models.VisitaObservacion,
    models.CorreccionDatos,
):
    admin.site.register(modelo)
