-- Datos iniciales de Donapp para las tablas de Django (core_*).
-- Uso: despues de "py manage.py migrate", ejecutar con psql:
--   psql -U postgres -d Donapp -f seed_donapp.sql
-- Es repetible: vacia las tablas core_* y las vuelve a llenar.

BEGIN;

TRUNCATE core_correcciondatos, core_visitaobservacion, core_visitadomiciliaria,
         core_donacionusuario, core_solicitud, core_donacion, core_evento,
         core_categoria, core_usuario RESTART IDENTITY CASCADE;

-- ============ USUARIOS ============
-- Contrasenas de Emily y DuvanT: mismos hashes bcrypt de antes, en formato Django.
-- Usuarios de prueba: pepito@correo.com -> contrasena "pepito"
--                     asistente@correo.com -> contrasena "asistente"
INSERT INTO core_usuario
 (id, password, last_login, is_superuser, nombre, apellido, tipo_documento, num_documento,
  fecha_nacimiento, direccion, email, telefono, necesidad, prioridad, observacion_visita, estado, rol)
VALUES
 (1, 'bcrypt$$2b$12$uaAk0qtwFlDTiU.5eQmHY..jY2pfZbEQAo0A8dxFYVDxRKuf64eaO', NULL, true,
  'Emily', 'Santana', 'CC', '1016834260', '2006-12-20', 'Ciudad Bolivar',
  'emisantvega@gmail.com', '3202006777', NULL, NULL, NULL, 'activo', 'administrador'),
 (2, 'bcrypt$$2b$10$kRS/B6yhX/rOiXB4D81sCeYMBG7nGB8u9TCotUWX32k/VO3mA49qq', NULL, true,
  'DuvanT', '', 'TI', '1023381752', '2008-10-16', 'Lisboa',
  'duvantimote16@gmail.com', '3213669365', NULL, NULL, NULL, 'activo', 'administrador'),
 (3, 'pbkdf2_sha256$1200000$WjxAl3AgCeOKecj0vuPE0S$qnlkfWlYtcuMTpvwAS4RvvQ3hmCSStH0zMUyekGkQ9w=', NULL, false,
  'Pepito Perez', '', 'CC', '1234567890', '1995-05-10', 'Calle Falsa 123',
  'pepito@correo.com', '300123', 'Busco apoyo alimentario', NULL, NULL, 'activo', 'donante'),
 (4, 'pbkdf2_sha256$1200000$WGd71M88437WprQetlW8oj$E3ilYhmCQsviBUt2IwohnIonQcK14whV50Uqv4MtZZg=', NULL, false,
  'Asistente', '', 'CC', '12345677655', '1995-05-11', 'Calle Falsa 1231',
  'asistente@correo.com', '300122233', NULL, NULL, NULL, 'activo', 'asistente');

-- ============ CATEGORIAS ============
INSERT INTO core_categoria (id, nombre, creado_por_id) VALUES
 (1,'Alimentos No Perecederos',1),(2,'Granos y Legumbres',2),(3,'Aceites y Grasas',1),
 (4,'Enlatados Varios',2),(5,'Leche en Polvo o Larga Vida',1),(6,'Suplementos Nutricionales Infantiles',2),
 (7,'Frutas y Verduras Frescas',1),(8,'Ropa para Bebés',2),(9,'Ropa para Niños y Niñas',1),
 (10,'Ropa para Adultos',2),(11,'Ropa Térmica y Chaquetas',1),(12,'Calzado Deportivo',2),
 (13,'Calzado Escolar',1),(14,'Calzado para Adultos',2),(15,'Muebles de Alcoba',1),
 (16,'Muebles de Sala y Comedor',2),(17,'Colchones y Colchonetas',1),(18,'Cobijas y Mantas',2),
 (19,'Sábanas y Fundas',1),(20,'Toallas y Paños',2),(21,'Utensilios de Cocina, Ollas y Vajilla',1),
 (22,'Electrodomésticos Pequeños',2),(23,'Cuadernos y Papelería',1),(24,'Libros de Texto Escolares',2),
 (25,'Literatura y Cuentos',1),(26,'Maletas y Morrales',2),(27,'Diccionarios y Enciclopedias',1),
 (28,'Instrumentos Musicales',2),(29,'Kits de Arte y Pintura',1),(30,'Computadores de Escritorio',2),
 (31,'Portátiles y Laptops',1),(32,'Tablets y Tablets Educativas',2),(33,'Teléfonos Móviles',1),
 (34,'Periféricos: Mouse, Teclado, Cámaras',2),(35,'Pañales Desechables',1),
 (36,'Productos de Aseo Personal',2),(37,'Higiene Femenina',1),(38,'Jabones y Detergentes',2),
 (39,'Elementos de Bioseguridad: Tapabocas',1),(40,'Juguetería Didáctica',2),
 (41,'Artículos Deportivos: Balones y Lazos',1),(42,'Juegos de Mesa',2);

-- ============ EVENTOS ============
INSERT INTO core_evento
 (id, nombre, contenido, imagen, fecha_publicacion, fecha_inicio, fecha_fin, lugar, estado)
VALUES
 (1,'Entrega de Mercados','Jornada de entrega de mercados a familias beneficiarias',NULL,
  '2026-01-20','2026-02-03','2026-02-03',
  'Transversal 73 H Bis #75B 46 Sur, Barrio Sierra Morena V Sector','publicado'),
 (2,'Entrega de Celulares','Jornada de entrega de dispositivos móviles donados',NULL,
  NULL,'2026-03-01','2026-03-02',
  'Transversal 73 H Bis #75B 46 Sur, Barrio Sierra Morena V Sector','borrador');

-- ============ DONACIONES ============
INSERT INTO core_donacion
 (id, descripcion, imagen, estado, fecha_creacion, observacion, stock, categoria_id)
VALUES
 (1,'Un kilo de azúcar marca blanca',NULL,'pendiente','2025-06-20 00:00:00',NULL,1,1),
 (2,'Un celular Motorola azul en buen estado',NULL,'pendiente','2025-06-20 00:00:00',NULL,1,33);

INSERT INTO core_donacionusuario (id, fecha_creacion, donante_id, donacion_id) VALUES
 (1,'2026-01-01',3,1),
 (2,'2026-02-02',3,2);

-- ============ SOLICITUDES ============
INSERT INTO core_solicitud
 (id, descripcion, estado, fecha_creacion, observacion, solicitante_id, categoria_id, gestor_id)
VALUES
 (1,'Solicito comida','aprobada','2026-11-12 07:38:22','Ninguna',3,1,1),
 (2,'Solicito un celular','aprobada','2026-11-12 07:38:22','Ninguna',3,33,2);

-- ============ VISITA DOMICILIARIA ============
INSERT INTO core_visitadomiciliaria
 (id, usuario_id, gestor_id, direccion, motivo, fecha_preferida, estado, observacion,
  fecha_solicitud, fecha_resolucion)
VALUES
 (1,3,NULL,'Calle Falsa 123','Verificar necesidad de alimentos reportada','2026-02-10',
  'pendiente',NULL,'2026-11-12 07:38:22',NULL);

-- ============ Reiniciar secuencias de ids ============
SELECT setval(pg_get_serial_sequence('core_usuario','id'), (SELECT max(id) FROM core_usuario));
SELECT setval(pg_get_serial_sequence('core_categoria','id'), (SELECT max(id) FROM core_categoria));
SELECT setval(pg_get_serial_sequence('core_evento','id'), (SELECT max(id) FROM core_evento));
SELECT setval(pg_get_serial_sequence('core_donacion','id'), (SELECT max(id) FROM core_donacion));
SELECT setval(pg_get_serial_sequence('core_donacionusuario','id'), (SELECT max(id) FROM core_donacionusuario));
SELECT setval(pg_get_serial_sequence('core_solicitud','id'), (SELECT max(id) FROM core_solicitud));
SELECT setval(pg_get_serial_sequence('core_visitadomiciliaria','id'), (SELECT max(id) FROM core_visitadomiciliaria));

COMMIT;
