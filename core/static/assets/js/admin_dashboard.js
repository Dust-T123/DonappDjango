/**
 * admin_dashboard.js
 * Lógica de UI del panel administrativo:
 * navegación de tabs, modales, validaciones, reportes PDF y helpers.
 */

// ── VALIDACIÓN: solo letras y espacios (bloquea la tecla, no solo limpia después) ──
function soloLetras(e) {
    const key   = e.key || String.fromCharCode(e.keyCode || e.which);
    const letras = /^[a-zA-ZáéíóúÁÉÍÓÚñÑüÜ\s]$/;
    return letras.test(key);
}

// ─────────────────────────────────────────────
// TABS DE NAVEGACIÓN (sidebar)
// ─────────────────────────────────────────────

/**
 * Activa un tab por selector de ancla (#dashboard, #usuarios, etc.)
 * @param {string} hash - ej. '#usuarios'
 */
function activarTab(hash) {
    document.querySelectorAll('.tab-pane').forEach(p => p.classList.remove('active'));
    document.querySelectorAll('.nav-link').forEach(l => l.classList.remove('active'));

    const target = document.querySelector(hash);
    if (target) target.classList.add('active');

    const link = document.querySelector(`.nav-link[href="${hash}"]`);
    if (link) link.classList.add('active');
}

// Activar tab según el hash de la URL al cargar
document.addEventListener('DOMContentLoaded', () => {
    const hash = window.location.hash || '#dashboard';
    activarTab(hash);

    // Escuchar clics en el sidebar
    document.querySelectorAll('.nav-link[href^="#"]').forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            const h = this.getAttribute('href');
            window.location.hash = h;
            activarTab(h);
        });
    });

    // Auto-ocultar mensajes flash
    ['flashMsg', 'flashNotif'].forEach(id => {
        const el = document.getElementById(id);
        if (el) setTimeout(() => el.style.display = 'none', 4000);
    });
});

// ─────────────────────────────────────────────
// TABS INTERNOS (Donaciones / Solicitudes)
// ─────────────────────────────────────────────

/**
 * Cambia entre los paneles internos dentro de una sección.
 * @param {HTMLElement} btn   - botón clickeado
 * @param {string}      panel - id del panel a mostrar
 */
function switchInner(btn, panel) {
    // Desactivar todos los botones y ocultar todos los paneles internos
    btn.closest('.tab-pane').querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    btn.closest('.tab-pane').querySelectorAll('.inner-panel').forEach(p => p.style.display = 'none');

    btn.classList.add('active');
    document.getElementById(panel).style.display = 'block';
}

// ─────────────────────────────────────────────
// MODALES — helpers genéricos
// ─────────────────────────────────────────────

function abrirModal(id) {
    document.getElementById(id).style.display = 'flex';
}

function cerrarModal(id) {
    document.getElementById(id).style.display = 'none';
}

// Cerrar modal al hacer clic fuera del contenido
document.addEventListener('click', function(e) {
    if (e.target.classList.contains('modal')) {
        e.target.style.display = 'none';
    }
});

// ─────────────────────────────────────────────
// MODAL — CREAR USUARIO
// ─────────────────────────────────────────────

function abrirModalCrearUsuario() {
    document.getElementById('formCrearUsuario').reset();
    toggleCamposDonante('nuevo_rol', 'grp_nuevo_prioridad', 'grp_nuevo_obs');
    abrirModal('modalCrearUsuario');
}

// Mostrar/ocultar campos exclusivos de donante en formularios
function toggleCamposDonante(rolSelectId, grpPrioridadId, grpObsId) {
    const rol = document.getElementById(rolSelectId).value;
    const mostrar = (rol === 'donante' || rol === '');
    document.getElementById(grpPrioridadId).style.display = mostrar ? 'block' : 'none';
    document.getElementById(grpObsId).style.display = mostrar ? 'block' : 'none';
}

// ─────────────────────────────────────────────
// MODAL — EDITAR USUARIO
// ─────────────────────────────────────────────

function abrirModalEditarUsuario(u) {
    document.getElementById('eu_id').value = u.idUsuario;
    document.getElementById('eu_nombre').value = u.nombre;
    document.getElementById('eu_tipo').value = u.tipoDocumento;
    document.getElementById('eu_doc').value = u.numDocumento;
    document.getElementById('eu_fnac').value = u.fechaNacimiento;
    document.getElementById('eu_dir').value = u.direccion;
    document.getElementById('eu_email').value = u.email;
    document.getElementById('eu_tel').value = u.telefono;
    document.getElementById('eu_nec').value = u.necesidad || '';
    document.getElementById('eu_rol').value = u.rol;
    document.getElementById('eu_estado').value = u.estado;
    document.getElementById('eu_pass').value = '';
    document.getElementById('eu_pass2').value = '';

    // Campos donante
    const prioEl = document.getElementById('eu_prioridad');
    const obsEl = document.getElementById('eu_obs_visita');
    if (prioEl) prioEl.value = u.prioridad || '';
    if (obsEl) obsEl.value = u.observacion_visita || '';

    toggleCamposDonante('eu_rol', 'grp_eu_prioridad', 'grp_eu_obs');
    abrirModal('modalEditarUsuario');
}

// ─────────────────────────────────────────────
// MODAL — VISITA DOMICILIARIA
// ─────────────────────────────────────────────

/**
 * Abre la modal de visita domiciliaria.
 * Bloquea controles y oculta el botón si la visita no está en estado editable.
 * @param {Object} data - Datos de la visita e historial.
 */
function abrirModalVisita(data) {
    const modal = document.getElementById('modalVisita');
    if (!modal) return;

    // Helper interno por si escHtml no está definido en el ámbito global
    const safeHtml = (str) => {
        if (typeof escHtml === 'function') return escHtml(str);
        if (!str) return '';
        return String(str)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');
    };

    // 1. Validar si la visita es editable
    const estadosEditables = ['pendiente'];
    const estadoActual = String(data?.estado || '').toLowerCase();
    const esEditable = estadosEditables.includes(estadoActual);

    // 2. Configurar el formulario y la ruta
    const formVisita = document.getElementById('formVisita');
    if (formVisita && data?.idVisita) {
        formVisita.action = `/admin/visitas/${data.idVisita}`;
    }

    // 3. Asignar estado actual al select
    const elEstado = document.getElementById('vis_estado');
    if (elEstado) {
        elEstado.value = data?.estado || '';
    }

    // 4. Bloquear / Desbloquear inputs, selectores y textareas
    const controles = modal.querySelectorAll('input, textarea, select');
    controles.forEach(control => {
        if (control.type === 'hidden') return;

        // Deshabilitar cualquier control si no es editable
        control.disabled = !esEditable;

        // Limpiar o restablecer campos de texto adicionales (ej. nueva observación)
        if (control.tagName === 'TEXTAREA' || (control.tagName === 'INPUT' && control.type === 'text')) {
            if (control.id !== 'vis_estado') {
                control.readOnly = !esEditable;
            }
        }
    });

    // Resetear el campo de nuevas observaciones al abrir
    const campoObs = document.getElementById('vis_obs');
    if (campoObs) {
        campoObs.value = '';
    }

    // 5. Visibilidad del botón de guardar
    const btnGuardar = modal.querySelector('button[type="submit"]');
    if (btnGuardar) {
        btnGuardar.style.display = esEditable ? 'inline-block' : 'none';
    }

    // 6. Renderizar historial / bitácora
    const contenedorHistorial = document.getElementById('vis_historial');
    if (contenedorHistorial) {
        if (Array.isArray(data?.historial) && data.historial.length > 0) {
            contenedorHistorial.innerHTML = data.historial.map(item => `
                <div class="historial-item" style="margin-bottom: 8px; padding: 8px; background: #f8f9fa; border-radius: 4px; border-left: 3px solid #0d6efd;">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <strong>${safeHtml(item.autor || 'Sistema')}</strong>
                        <small class="text-muted">${safeHtml(item.fecha || '')}</small>
                    </div>
                    <p style="margin: 4px 0 0 0; color: #333;">${safeHtml(item.texto || '')}</p>
                </div>
            `).join('');
        } else {
            contenedorHistorial.innerHTML = '<p class="text-muted" style="margin: 0; font-size: 0.9rem;">Sin notas registradas en la bitácora.</p>';
        }
    }

    // 7. Mostrar la modal
    if (typeof abrirModal === 'function') {
        abrirModal('modalVisita');
    } else {
        modal.classList.add('show');
        modal.style.display = 'block';
    }
}

// ─────────────────────────────────────────────
// MODAL — GESTIONAR DONACIÓN
// ─────────────────────────────────────────────

function abrirModalDonacion(d) {
    document.getElementById('don_id').value = d.idDonacion;

    const estadoSel = document.getElementById('don_estado');
    estadoSel.value = d.estado;
    document.getElementById('don_obs').value = d.observacion || '';

    // Construir bloque de detalle
    let imgHtml = '';
    if (d.imagen) {
        imgHtml = `<img src="${d.imagen}" class="detalle-img" alt="Imagen donación">`;
    }
    document.getElementById('don_detalle').innerHTML = `
        ${imgHtml}
        <p><strong>ID:</strong> ${d.idDonacion}</p>
        <p><strong>Descripción:</strong> ${escHtml(d.descripcion)}</p>
        <p><strong>Categoría:</strong> ${escHtml(d.categoria || '—')}</p>
        <p><strong>Stock:</strong> ${d.stock}</p>
        <p><strong>Donante:</strong> ${escHtml(d.donante || '—')}</p>
        <p><strong>Fecha:</strong> ${formatearFecha(d.fechaCreacion)}</p>
    `;

    actualizarHintObservacion('don_estado', 'don_obs_hint', 'don_obs', 'don_obs_err');
    abrirModal('modalDonacion');
}

// ─────────────────────────────────────────────
// MODAL — GESTIONAR SOLICITUD
// ─────────────────────────────────────────────

function abrirModalSolicitud(s) {
    document.getElementById('sol_id').value = s.idSolicitud;

    const estadoSel = document.getElementById('sol_estado');
    estadoSel.value = s.estado;
    document.getElementById('sol_obs').value = s.observacion || '';

    let imgHtml = '';
    if (s.imagen) {
        imgHtml = `<img src="${s.imagen}" class="detalle-img" alt="Imagen solicitud">`;
    }
    document.getElementById('sol_detalle').innerHTML = `
        ${imgHtml}
        <p><strong>ID:</strong> ${s.idSolicitud}</p>
        <p><strong>Descripción:</strong> ${escHtml(s.descripcion)}</p>
        <p><strong>Categoría:</strong> ${escHtml(s.categoria || '—')}</p>
        <p><strong>Solicitante:</strong> ${escHtml(s.nombre_solicitante || '—')}</p>
        <p><strong>Gestor:</strong> ${escHtml(s.nombre_gestor || 'Sin asignar')}</p>
        <p><strong>Fecha:</strong> ${formatearFecha(s.fechaCreacion)}</p>
    `;

    actualizarHintObservacion('sol_estado', 'sol_obs_hint', 'sol_obs', 'sol_obs_err');
    abrirModal('modalSolicitud');
}

// ─────────────────────────────────────────────
// MODAL — CREAR EVENTO
// ─────────────────────────────────────────────

function abrirModalCrearEvento() {
    abrirModal('modalCrearEvento');
}

// ─────────────────────────────────────────────
// MODAL — EDITAR EVENTO
// ─────────────────────────────────────────────

function abrirModalEditarEvento(ev) {
    document.getElementById('edit_idEvento').value = ev.idEvento;
    document.getElementById('edit_nombre').value = ev.Nombre;
    document.getElementById('edit_estado').value = ev.estado;
    document.getElementById('edit_fecha_inicio').value = ev.fecha_inicio || '';
    document.getElementById('edit_fecha_fin').value = ev.fecha_fin || '';
    document.getElementById('edit_lugar_entrega').value = ev.lugar_entrega || '';
    document.getElementById('edit_titulo_pub').value = ev.titulo_pub || '';
    document.getElementById('edit_contenido_pub').value = ev.contenido_pub || '';

    // Solo bloqueamos fechas pasadas si el evento aún no terminó; si ya es
    // un evento histórico, no forzamos el mínimo o sería imposible guardar
    // cualquier otro cambio en él sin cambiarle también las fechas.
    const hoyStr = new Date().toISOString().split('T')[0];
    const finInput = document.getElementById('edit_fecha_fin');
    finInput.min = (ev.fecha_fin && ev.fecha_fin < hoyStr) ? '' : hoyStr;

    const preview = document.getElementById('edit_img_preview');
    const wrap = document.getElementById('edit_img_preview_wrap');
    if (ev.imagen) {
        preview.src = ev.imagen;
        wrap.style.display = 'block';
    } else {
        wrap.style.display = 'none';
    }

    // Limpiar preview de nueva imagen
    const nuevaPreview = document.getElementById('edit_nueva_img_preview');
    nuevaPreview.src = '';
    nuevaPreview.style.display = 'none';
    document.getElementById('edit_imagen_pub').value = '';

    abrirModal('modalEditarEvento');
}

/**
 * Muestra un preview de la imagen seleccionada para reemplazo.
 * @param {HTMLInputElement} input
 */
function previewNuevaImagen(input) {
    const preview = document.getElementById('edit_nueva_img_preview');
    if (input.files && input.files[0]) {
        const reader = new FileReader();
        reader.onload = e => {
            preview.src = e.target.result;
            preview.style.display = 'block';
        };
        reader.readAsDataURL(input.files[0]);
    }
}

// ─────────────────────────────────────────────
// MODAL — CATEGORÍAS
// ─────────────────────────────────────────────

function abrirModalEditarCategoria(cat) {
    document.getElementById('ecat_id').value = cat.idCategoria;
    document.getElementById('ecat_nombre').value = cat.nombre;
    abrirModal('modalEditarCategoria');
}

// ─────────────────────────────────────────────
// VALIDACIONES
// ─────────────────────────────────────────────

/**
 * Valida que dos campos de contraseña coincidan.
 * @returns {boolean}
 */
function validarPassModal(passId, pass2Id, errId) {
    const p1 = document.getElementById(passId).value;
    const p2 = document.getElementById(pass2Id).value;
    const err = document.getElementById(errId);

    if (p1 && p1 !== p2) {
        err.style.display = 'block';
        return false;
    }
    err.style.display = 'none';
    return true;
}

/** Validación específica del perfil (alias semántico) */
function validarPassPerfil() {
    return validarPassModal('perfil_pass', 'perfil_pass2', 'perfil_pass_err');
}

/** Validación completa del formulario de perfil (contraseñas + campos obligatorios) */
function validarFormularioCompleto() {
    return validarPassPerfil();
}

/**
 * Valida que la observación esté presente cuando el estado es "rechazada".
 */
function validarObservacionRequerida(estadoId, obsId, errId) {
    const estado = document.getElementById(estadoId).value;
    const obs = document.getElementById(obsId).value.trim();
    const err = document.getElementById(errId);

    if (estado === 'rechazada' && !obs) {
        err.style.display = 'block';
        return false;
    }
    err.style.display = 'none';
    return true;
}

/**
 * Actualiza el hint de observación según el estado seleccionado.
 */
function actualizarHintObservacion(estadoId, hintId, obsId, errId) {
    const estado = document.getElementById(estadoId).value;
    const hint = document.getElementById(hintId);
    const obs = document.getElementById(obsId);
    const err = document.getElementById(errId);

    if (estado === 'rechazada') {
        hint.textContent = '(obligatorio al rechazar)';
        hint.style.color = '#c62828';
        obs.style.borderColor = '#c62828';
    } else {
        hint.textContent = '(opcional)';
        hint.style.color = '';
        obs.style.borderColor = '';
    }

    if (err) err.style.display = 'none';
}

/**
 * Valida caracteres permitidos en el nombre de una categoría.
 * @param {HTMLInputElement} input
 */
function validarEntrada(input) {
    const patron = /^[a-zA-ZáéíóúÁÉÍÓÚñÑüÜ\s\-()]*$/;
    const errId = input.id === 'cat_nombre' ? 'cat_err' : 'ecat_err';
    const errEl = document.getElementById(errId);

    // Las categorías nunca llevan números: se limpia en vivo, igual que en el panel de asistente.
    const valorLimpio = input.value.replace(/[^a-zA-ZáéíóúÁÉÍÓÚñÑüÜ\s\-()]/g, '');
    if (input.value !== valorLimpio) {
        input.value = valorLimpio;
    }

    if (!patron.test(input.value) && input.value !== '') {
        errEl.textContent = 'Solo se permiten letras, espacios, guiones y paréntesis (nunca números).';
        errEl.style.display = 'inline';
        input.style.borderColor = '#c62828';
    } else {
        errEl.style.display = 'none';
        input.style.borderColor = '';
    }
}

/**
 * Valida el formulario de categoría antes de enviar.
 * @param {'crear'|'editar'} modo
 */
function validarCategoria(modo) {
    const inputId = modo === 'crear' ? 'cat_nombre' : 'ecat_nombre';
    const errId = modo === 'crear' ? 'cat_err' : 'ecat_err';
    const input = document.getElementById(inputId);
    const errEl = document.getElementById(errId);
    const patron = /^[a-zA-ZáéíóúÁÉÍÓÚñÑüÜ0-9\s\-_.,()]+$/;

    if (!patron.test(input.value.trim())) {
        errEl.textContent = 'Caracteres no permitidos en el nombre.';
        errEl.style.display = 'inline';
        return false;
    }
    return true;
}

// ─────────────────────────────────────────────
// TOGGLE PRIORIDAD (filtro de usuarios)
// ─────────────────────────────────────────────

function togglePrioridadFiltro() {
    const rol = document.getElementById('filtro_rol_select').value;
    const prioEl = document.getElementById('filtro_prioridad_select');
    if (rol === '' || rol === 'donante') {
        prioEl.style.display = 'inline-block';
    } else {
        prioEl.style.display = 'none';
        prioEl.value = '';
    }
}

// ─────────────────────────────────────────────
// TOGGLE CONTRASEÑA (mostrar/ocultar)
// ─────────────────────────────────────────────

/**
 * @param {string} inputId - id del campo password
 * @param {string} iconId  - id del ícono fa-eye
 */
function togglePass(inputId, iconId) {
    const input = document.getElementById(inputId);
    const icon = document.getElementById(iconId);
    if (input.type === 'password') {
        input.type = 'text';
        icon.classList.replace('fa-eye', 'fa-eye-slash');
    } else {
        input.type = 'password';
        icon.classList.replace('fa-eye-slash', 'fa-eye');
    }
}

// ─────────────────────────────────────────────
// REPORTES PDF (jsPDF + AutoTable)
// ─────────────────────────────────────────────

function formatearFecha(fechaStr) {
    if (!fechaStr) return '—';
    const partes = String(fechaStr).substring(0, 10).split('-');
    if (partes.length === 3) return `${partes[2]}/${partes[1]}/${partes[0]}`;
    return fechaStr;
}
function generarReporteDonaciones() {
    const estado = document.getElementById('rpt_don_estado').value;
    const desde = document.getElementById('rpt_don_desde').value;
    const hasta = document.getElementById('rpt_don_hasta').value;

    let datos = JSON.parse(document.getElementById('donacionesData').textContent);

    // Filtrar
    datos = datos.filter(d => {
        if (estado !== 'todos' && d.estado !== estado) return false;
        if (desde && d.fechaCreacion < desde) return false;
        if (hasta && d.fechaCreacion > hasta + ' 23:59:59') return false;
        return true;
    });

    const { jsPDF } = window.jspdf;
    const doc = new jsPDF({ orientation: 'landscape' });

    doc.setFontSize(16);
    doc.text('Reporte de Donaciones — Donapp', 14, 15);
    doc.setFontSize(10);
    doc.text(`Generado: ${new Date().toLocaleString('es-CO')}  |  Total: ${datos.length}`, 14, 22);

    doc.autoTable({
        startY: 27,
        head: [
            ['#', 'Descripción', 'Categoría', 'Stock', 'Estado', 'Fecha', 'Donante', 'Observación']
        ],
        body: datos.map(d => [
            d.idDonacion,
            d.descripcion,
            d.categoria || '—',
            d.stock,
            d.estado,
            d.fechaCreacion ? d.fechaCreacion.substring(0, 10) : '—',
            d.donante || '—',
            d.observacion || '—'
        ]),
        styles: { fontSize: 8, cellPadding: 2 },
        headStyles: { fillColor: [11, 90, 166] },
        alternateRowStyles: { fillColor: [227, 237, 251] }
    });

    doc.save(`donaciones_${new Date().toISOString().slice(0,10)}.pdf`);
}

function generarReporteSolicitudes() {
    const estado = document.getElementById('rpt_sol_estado').value;
    const desde = document.getElementById('rpt_sol_desde').value;
    const hasta = document.getElementById('rpt_sol_hasta').value;

    let datos = JSON.parse(document.getElementById('solicitudesData').textContent);

    datos = datos.filter(s => {
        if (estado !== 'todos' && s.estado !== estado) return false;
        if (desde && s.fechaCreacion < desde) return false;
        if (hasta && s.fechaCreacion > hasta + ' 23:59:59') return false;
        return true;
    });

    const { jsPDF } = window.jspdf;
    const doc = new jsPDF({ orientation: 'landscape' });

    doc.setFontSize(16);
    doc.text('Reporte de Solicitudes — Donapp', 14, 15);
    doc.setFontSize(10);
    doc.text(`Generado: ${new Date().toLocaleString('es-CO')}  |  Total: ${datos.length}`, 14, 22);

    doc.autoTable({
        startY: 27,
        head: [
            ['#', 'Descripción', 'Categoría', 'Estado', 'Fecha', 'Solicitante', 'Observación']
        ],
        body: datos.map(s => [
            s.idSolicitud,
            s.descripcion,
            s.categoria || '—',
            s.estado,
            s.fechaCreacion ? s.fechaCreacion.substring(0, 10) : '—',
            s.solicitante || '—',
            s.observacion || '—'
        ]),
        styles: { fontSize: 8, cellPadding: 2 },
        headStyles: { fillColor: [25, 118, 210] },
        alternateRowStyles: { fillColor: [227, 242, 253] }
    });

    doc.save(`solicitudes_${new Date().toISOString().slice(0,10)}.pdf`);
}

// ─────────────────────────────────────────────
// UTILIDADES
// ─────────────────────────────────────────────

/** Escapa HTML para evitar XSS al inyectar texto en el DOM. */
function escHtml(str) {
    if (!str) return '';
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;');
}