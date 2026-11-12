from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='solicitud',
            name='estado',
            field=models.CharField(choices=[('pendiente', 'pendiente'), ('aprobada', 'aprobada'), ('rechazada', 'rechazada'), ('cancelada', 'cancelada'), ('completada', 'completada')], default='pendiente', max_length=15),
        ),
        migrations.AlterField(
            model_name='correcciondatos',
            name='campo',
            field=models.CharField(choices=[('nombre', 'nombre'), ('apellido', 'apellido'), ('tipoDocumento', 'tipoDocumento'), ('numDocumento', 'numDocumento'), ('fechaNacimiento', 'fechaNacimiento')], max_length=20),
        ),
        migrations.AddConstraint(
            model_name='donacion',
            constraint=models.CheckConstraint(condition=models.Q(('stock__gte', 0)), name='chk_donacion_stock_no_negativo'),
        ),
        migrations.AddConstraint(
            model_name='evento',
            constraint=models.CheckConstraint(condition=models.Q(('fecha_inicio__isnull', True), ('fecha_fin__isnull', True), ('fecha_fin__gte', models.F('fecha_inicio')), _connector='OR'), name='chk_evento_rango_fechas'),
        ),
    ]
