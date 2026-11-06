from datetime import date

from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.core.exceptions import ValidationError
from django.db import models


def opciones(*valores):
    return [(valor, valor) for valor in valores]


TIPOS_DOCUMENTO = opciones('CC', 'TI', 'CE', 'TE', 'PPT', 'Pasaporte')
PRIORIDADES = opciones('urgente', 'alta', 'media', 'baja')
ESTADOS_USUARIO = opciones('activo', 'inactivo')
ROLES = opciones('donante', 'asistente', 'administrador')
ESTADOS_EVENTO = opciones('borrador', 'publicado', 'en_curso', 'finalizado', 'cancelado')
ESTADOS_DONACION = opciones('pendiente', 'aprobada', 'cancelada', 'completada', 'rechazada')
ESTADOS_VISITA = opciones('pendiente', 'aprobada', 'rechazada', 'realizada', 'cancelada')
ESTADOS_CORRECCION = opciones('pendiente', 'aprobada', 'rechazada')
CAMPOS_CORRECCION = opciones('nombre', 'apellido', 'tipo_documento', 'num_documento', 'fecha_nacimiento')

LUGAR_ENTREGA = 'Transversal 73 H Bis #75B 46 Sur, Barrio Sierra Morena V Sector'


def calcular_edad(fecha_nacimiento):
    hoy = date.today()
    cumplio = (hoy.month, hoy.day) >= (fecha_nacimiento.month, fecha_nacimiento.day)
    return hoy.year - fecha_nacimiento.year - (0 if cumplio else 1)


def validar_edad_minima(fecha_nacimiento):
    if calcular_edad(fecha_nacimiento) < 14:
        raise ValidationError('El usuario debe tener al menos 14 años.')


class UsuarioManager(BaseUserManager):
    def create_user(self, email, password=None, **campos):
        if not email:
            raise ValueError('El correo es obligatorio')
        usuario = self.model(email=self.normalize_email(email), **campos)
        usuario.set_password(password)
        usuario.save(using=self._db)
        return usuario

    def create_superuser(self, email, password=None, **campos):
        campos.setdefault('rol', 'administrador')
        campos.setdefault('is_superuser', True)
        return self.create_user(email, password, **campos)


class Usuario(AbstractBaseUser, PermissionsMixin):
    nombre = models.CharField(max_length=100)
    apellido = models.CharField(max_length=100, blank=True, default='')
    tipo_documento = models.CharField(max_length=10, choices=TIPOS_DOCUMENTO)
    num_documento = models.CharField(max_length=20, unique=True)
    fecha_nacimiento = models.DateField(validators=[validar_edad_minima])
    direccion = models.CharField(max_length=255)
    email = models.EmailField(max_length=150, unique=True)
    telefono = models.CharField(max_length=15)
    necesidad = models.CharField(max_length=255, null=True, blank=True)
    prioridad = models.CharField(max_length=10, choices=PRIORIDADES, null=True, blank=True)
    observacion_visita = models.CharField(max_length=500, null=True, blank=True)
    estado = models.CharField(max_length=10, choices=ESTADOS_USUARIO, default='activo')
    rol = models.CharField(max_length=15, choices=ROLES, default='donante')

    objects = UsuarioManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['nombre', 'tipo_documento', 'num_documento', 'fecha_nacimiento', 'direccion', 'telefono']

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(rol='donante') | models.Q(necesidad__isnull=True, prioridad__isnull=True),
                name='chk_solo_donante_necesidad',
            )
        ]

    @property
    def is_active(self):
        return self.estado == 'activo'

    @property
    def is_staff(self):
        return self.rol in ('administrador', 'asistente')

    @property
    def edad(self):
        return calcular_edad(self.fecha_nacimiento)

    def __str__(self):
        return f'{self.nombre} {self.apellido}'.strip()


class Categoria(models.Model):
    nombre = models.CharField(max_length=100)
    creado_por = models.ForeignKey(
        Usuario, null=True, blank=True, on_delete=models.SET_NULL, related_name='categorias_creadas'
    )

    def __str__(self):
        return self.nombre


class Evento(models.Model):
    nombre = models.CharField(max_length=150)
    contenido = models.TextField(null=True, blank=True)
    imagen = models.ImageField(upload_to='eventos/', null=True, blank=True)
    fecha_publicacion = models.DateField(null=True, blank=True)
    fecha_inicio = models.DateField(null=True, blank=True)
    fecha_fin = models.DateField(null=True, blank=True)
    lugar = models.CharField(max_length=255, null=True, blank=True, default=LUGAR_ENTREGA)
    estado = models.CharField(max_length=15, choices=ESTADOS_EVENTO, default='borrador')

    def __str__(self):
        return self.nombre


class Donacion(models.Model):
    descripcion = models.CharField(max_length=200)
    imagen = models.ImageField(upload_to='donaciones/', null=True, blank=True)
    estado = models.CharField(max_length=15, choices=ESTADOS_DONACION, default='pendiente')
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    observacion = models.CharField(max_length=200, null=True, blank=True)
    stock = models.IntegerField(default=0)
    categoria = models.ForeignKey(
        Categoria, null=True, blank=True, on_delete=models.SET_NULL, related_name='donaciones'
    )

    class Meta:
        verbose_name_plural = 'donaciones'

    def __str__(self):
        return self.descripcion


class Solicitud(models.Model):
    descripcion = models.CharField(max_length=300)
    estado = models.CharField(max_length=15, choices=ESTADOS_DONACION, default='pendiente')
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    observacion = models.CharField(max_length=300, null=True, blank=True)
    solicitante = models.ForeignKey(
        Usuario, null=True, blank=True, on_delete=models.SET_NULL,
        related_name='solicitudes', limit_choices_to={'rol': 'donante'},
    )
    categoria = models.ForeignKey(
        Categoria, null=True, blank=True, on_delete=models.SET_NULL, related_name='solicitudes'
    )
    gestor = models.ForeignKey(
        Usuario, null=True, blank=True, on_delete=models.SET_NULL, related_name='solicitudes_gestionadas'
    )

    class Meta:
        verbose_name_plural = 'solicitudes'

    def clean(self):
        if self.solicitante and self.solicitante.rol != 'donante':
            raise ValidationError('Solo los usuarios con rol donante pueden crear solicitudes.')

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.descripcion


class DonacionUsuario(models.Model):
    fecha_creacion = models.DateField(auto_now_add=True)
    donante = models.ForeignKey(
        Usuario, null=True, blank=True, on_delete=models.SET_NULL,
        related_name='donaciones_realizadas', limit_choices_to={'rol': 'donante'},
    )
    donacion = models.ForeignKey(
        Donacion, null=True, blank=True, on_delete=models.SET_NULL, related_name='donantes'
    )

    def clean(self):
        if self.donante and self.donante.rol != 'donante':
            raise ValidationError('Solo los usuarios con rol donante pueden realizar donaciones.')

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)


class VisitaDomiciliaria(models.Model):
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='visitas')
    gestor = models.ForeignKey(
        Usuario, null=True, blank=True, on_delete=models.SET_NULL, related_name='visitas_gestionadas'
    )
    direccion = models.CharField(max_length=255)
    motivo = models.CharField(max_length=300)
    fecha_preferida = models.DateField(null=True, blank=True)
    estado = models.CharField(max_length=15, choices=ESTADOS_VISITA, default='pendiente')
    observacion = models.CharField(max_length=300, null=True, blank=True)
    fecha_solicitud = models.DateTimeField(auto_now_add=True)
    fecha_resolucion = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name_plural = 'visitas domiciliarias'
        indexes = [models.Index(fields=['usuario', 'estado'])]


class VisitaObservacion(models.Model):
    visita = models.ForeignKey(VisitaDomiciliaria, on_delete=models.CASCADE, related_name='observaciones')
    usuario = models.ForeignKey(
        Usuario, null=True, blank=True, on_delete=models.SET_NULL, related_name='observaciones_escritas'
    )
    texto = models.CharField(max_length=500)
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = 'observaciones de visita'


class CorreccionDatos(models.Model):
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='correcciones')
    solicitante = models.ForeignKey(
        Usuario, null=True, blank=True, on_delete=models.SET_NULL, related_name='correcciones_solicitadas'
    )
    campo = models.CharField(max_length=20, choices=CAMPOS_CORRECCION)
    valor_anterior = models.CharField(max_length=255)
    valor_nuevo = models.CharField(max_length=255)
    justificacion = models.CharField(max_length=300)
    estado = models.CharField(max_length=15, choices=ESTADOS_CORRECCION, default='pendiente')
    aprobador = models.ForeignKey(
        Usuario, null=True, blank=True, on_delete=models.SET_NULL, related_name='correcciones_aprobadas'
    )
    fecha_solicitud = models.DateTimeField(auto_now_add=True)
    fecha_resolucion = models.DateTimeField(null=True, blank=True)
    observacion_resolucion = models.CharField(max_length=300, null=True, blank=True)
    soporte_ruta = models.CharField(max_length=255, null=True, blank=True)
    soporte_mime = models.CharField(max_length=100, null=True, blank=True)
    soporte_hash = models.CharField(max_length=64, null=True, blank=True)
    consentimiento = models.BooleanField(default=False)

    class Meta:
        verbose_name_plural = 'correcciones de datos'