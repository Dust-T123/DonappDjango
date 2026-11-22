# DonappDjango

Plataforma de donaciones (Django + PostgreSQL) para la fundación CES Waldorf, Ciudad Bolívar.

## Requisitos

- Python 3.13
- Git
- PostgreSQL (incluye `psql`) y, opcionalmente, pgAdmin
- Archivo `.env` con los datos de conexión (no está en el repositorio; pídelo al equipo)

## Puesta en marcha en un computador nuevo

Todos los comandos son para PowerShell, desde la carpeta del proyecto.

### 1. Clonar y entrar a la rama de trabajo

```powershell
git clone https://github.com/Dust-T123/DonappDjango.git
cd DonappDjango
git checkout <tu-rama>
```

### 2. Entorno virtual y dependencias

```powershell
py -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Si PowerShell bloquea la activación:
`Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned`

### 3. Archivo `.env`

Copia el `.env` a la raíz del proyecto (junto a `manage.py`). Debe llamarse exactamente `.env`
y contener los datos de tu PostgreSQL local (nombre de la BD, usuario, contraseña, host y puerto).

### 4. Crear la base de datos vacía

En pgAdmin: clic derecho en **Databases → Create → Database**, con el mismo nombre que
el `.env` (por ejemplo `Donapp`). O por consola:

```powershell
& "C:\Program Files\PostgreSQL\<version>\bin\psql.exe" -U postgres -c "CREATE DATABASE \"Donapp\";"
```

### 5. Crear las tablas

```powershell
py manage.py migrate
```

### 6. Cargar los datos iniciales

```powershell
$env:PGCLIENTENCODING="UTF8"
& "C:\Program Files\PostgreSQL\<version>\bin\psql.exe" -U postgres -d Donapp -f seed_donapp.sql
```

Ajusta `<version>` a la carpeta que exista en `C:\Program Files\PostgreSQL`.
El script se puede volver a ejecutar cuando quieras: borra los datos de las tablas `core_*`
y los vuelve a cargar.

### 7. Ejecutar

```powershell
py manage.py runserver
```

Abrir <http://127.0.0.1:8000/>.

## Usuarios de prueba

| Rol           | Correo                    | Contraseña             |
|---------------|---------------------------|------------------------|
| Administrador | emisantvega@gmail.com     | la de Emily            |
| Administrador | duvantimote16@gmail.com   | la de Duvan            |
| Donante       | pepito@correo.com         | `pepito`               |
| Asistente     | asistente@correo.com      | `asistente`            |

Los datos de ejemplo incluyen 42 categorías, 2 eventos, 2 donaciones, 2 solicitudes y 1 visita domiciliaria.

## Notas

- Django usa las tablas `core_*`. Las tablas sin ese prefijo (`usuario`, `categoria`, ...) vienen
  de un volcado antiguo de PostgreSQL y **no se usan**; no hace falta restaurarlo.
- Nunca subas el `.env` al repositorio.
- Antes de empezar a trabajar: `git pull origin <tu-rama>`. Al terminar:
  `git add .`, `git commit -m "mensaje"`, `git push origin <tu-rama>`.

## Problemas frecuentes

- `No module named 'xxx'`: el entorno virtual no está activo o faltan dependencias
  (`pip install -r requirements.txt`).
- `password authentication failed`: la contraseña del `.env` no coincide con la de tu PostgreSQL.
- La página muestra `+0` y no hay usuarios: falta el paso 6 (cargar `seed_donapp.sql`).
