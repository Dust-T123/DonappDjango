// Lógica del panel del administrador que en Laravel vivía en un <script> dentro del Blade.
// Las URLs y el id del admin llegan desde el template (ver dashboard_administrador.html).
const ROUTES = window.ROUTES_ADM;

function abrirModalVisita(v) {
    const editable = !!v.editable;
    const form = document.getElementById('formVisita');
    const estadoSel = document.getElementById('vis_estado');
    const obsField = document.getElementById('vis_obs');

    form.action = editable ? ROUTES.visita(v.idVisita) : ROUTES.visitaNota(v.idVisita);

    document.getElementById('vis_estado_group').style.display = editable ? '' : 'none';
    estadoSel.disabled = !editable;          // los select deshabilitados no se envían con el form
    estadoSel.value = (v.estado === 'pendiente') ? 'aprobada' : v.estado;

    document.getElementById('vis_locked_msg').style.display = editable ? 'none' : '';
    document.getElementById('vis_titulo').innerHTML = editable
        ? '<i class="fa-solid fa-house-chimney-user"></i> Gestionar Visita Domiciliaria'
        : '<i class="fa-solid fa-house-chimney-user"></i> Visita Domiciliaria (finalizada)';

    // El nombre del campo cambia según el endpoint: 'observacion' (opcional,
    // acompaña el cambio de estado) vs 'texto' (nota suelta a la bitácora).
    obsField.name = editable ? 'observacion' : 'texto';
    obsField.required = !editable;
    obsField.value = '';
    document.getElementById('vis_submit').innerHTML = editable
        ? '<i class="fa-solid fa-floppy-disk"></i> Guardar'
        : '<i class="fa-solid fa-note-sticky"></i> Agregar nota';

    document.getElementById('vis_detalle').innerHTML =
        `<p><strong>Beneficiario:</strong> ${escHtml(v.usuario || '—')}</p>`;

    const hist = v.historial || [];
    document.getElementById('vis_historial').innerHTML = hist.length
        ? hist.map(h => `
            <div class="bitacora-item">
                <div class="bitacora-meta"><strong>${escHtml(h.autor)}</strong> · ${escHtml(h.fecha)}</div>
                <div class="bitacora-texto">${escHtml(h.texto)}</div>
            </div>`).join('')
        : '<p class="text-muted" style="font-size:0.85rem">Aún no hay notas en la bitácora.</p>';

    abrirModal('modalVisita');
}

// Sobrescribir abrirModalDonacion para inyectar la ruta correcta
const _origAbrirDon = window.abrirModalDonacion;
window.abrirModalDonacion = function(d) {
    if (_origAbrirDon) _origAbrirDon(d);
    document.getElementById('formDonacion').action = ROUTES.donacion(d.idDonacion);
    document.getElementById('don_id').value = d.idDonacion;
};

const _origAbrirSol = window.abrirModalSolicitud;
window.abrirModalSolicitud = function(s) {
    if (_origAbrirSol) _origAbrirSol(s);
    document.getElementById('formSolicitud').action = ROUTES.solicitud(s.idSolicitud);
    document.getElementById('sol_id').value = s.idSolicitud;
};

// Editar usuario: inyectar acción con ID dinámico
// Reescribimos por completo (no delegamos al JS externo) porque los campos
// sensibles ahora son <input disabled> de solo lectura, no <select>/<input> editables.
window.abrirModalEditarUsuario = function(u) {
    // Si el admin intenta editarse a sí mismo desde la lista general, lo
    // mandamos a "Mi perfil" (con su propio flujo de corrección de datos)
    // en vez de abrir el modal genérico de edición de usuarios.
    if (String(u.idUsuario) === String(window.ADMIN_ID)) {
        activarTab('#perfil');
        return;
    }
    document.getElementById('formEditarUsuario').action = ROUTES.editarUsuario(u.idUsuario);
    document.getElementById('eu_id').value          = u.idUsuario;
    document.getElementById('eu_nombre').value       = u.nombre;
    document.getElementById('eu_apellido').value      = u.apellido || '';
    document.getElementById('eu_tipo_display').value = u.tipoDocumento;
    document.getElementById('eu_doc').value          = u.numDocumento;
    document.getElementById('eu_fnac').value         = u.fechaNacimiento;
    document.getElementById('eu_dir').value          = u.direccion;
    document.getElementById('eu_email').value        = u.email;
    document.getElementById('eu_tel').value          = u.telefono;
    document.getElementById('eu_nec').value          = u.necesidad || '';
    document.getElementById('eu_rol').value          = u.rol;
    document.getElementById('eu_estado').value       = u.estado;
    document.getElementById('eu_pass').value         = '';
    document.getElementById('eu_pass2').value        = '';

    const prioEl = document.getElementById('eu_prioridad');
    const obsEl  = document.getElementById('eu_obs_visita');
    if (prioEl) prioEl.value = u.prioridad || '';
    if (obsEl)  obsEl.value  = u.observacion_visita || '';

    toggleCamposDonante('eu_rol', 'grp_eu_prioridad', 'grp_eu_obs');

    // Guardamos el usuario objetivo para el botón "Solicitar corrección"
    window._usuarioEnEdicion = { idUsuario: u.idUsuario, nombre: u.nombre };

    abrirModal('modalEditarUsuario');
};

// Abre el modal de solicitud de corrección para el usuario que se está editando
function abrirModalCorreccionUsuario() {
    const u = window._usuarioEnEdicion;
    if (!u) return;
    document.getElementById('cu_nombre_usuario').textContent = u.nombre;
    document.getElementById('formCorreccionUsuario').action  = ROUTES.solicitarCorreccionUsuario(u.idUsuario);
    document.getElementById('formCorreccionUsuario').reset();
    abrirModal('modalCorreccionUsuario');
}

// Editar categoría: inyectar acción con ID dinámico
const _origEditCat = window.abrirModalEditarCategoria;
window.abrirModalEditarCategoria = function(c) {
    if (_origEditCat) _origEditCat(c);
    document.getElementById('formEditarCategoria').action = ROUTES.editarCategoria(c.idCategoria);
    document.getElementById('ecat_id').value = c.idCategoria;
    document.getElementById('ecat_nombre').value = c.nombre;
    abrirModal('modalEditarCategoria');
};

// Editar evento: inyectar acción con ID dinámico
const _origEditEvt = window.abrirModalEditarEvento;
window.abrirModalEditarEvento = function(ev) {
    if (_origEditEvt) _origEditEvt(ev);
    document.getElementById('formEditarEvento').action = ROUTES.editarEvento(ev.idEvento);
};

// ══════════ VALIDACIÓN: CATEGORÍAS DUPLICADAS (cliente) ══════════
// El backend SIEMPRE debe validar de nuevo (ver trigger tg_validar_categoria_duplicada);
// esto solo evita un viaje al servidor innecesario y da feedback inmediato.
function categoriasExistentesList() {
    const el = document.getElementById('categoriasExistentes');
    if (!el) return [];
    try { return JSON.parse(el.textContent); } catch (e) { return []; }
}

function nombreCategoriaDuplicado(nombre, idExcluir = null) {
    const normalizado = nombre.trim().toLowerCase();
    return categoriasExistentesList().some(c =>
        c.nombre === normalizado && (idExcluir === null || String(c.id) !== String(idExcluir))
    );
}

const _origValidarCategoria = window.validarCategoria;
window.validarCategoria = function(modo) {
    // Deja que la validación original (longitud, caracteres, etc.) corra primero si existe
    if (typeof _origValidarCategoria === 'function' && _origValidarCategoria(modo) === false) {
        return false;
    }
    const inputId = modo === 'crear' ? 'cat_nombre' : 'ecat_nombre';
    const errId    = modo === 'crear' ? 'cat_err'    : 'ecat_err';
    const input    = document.getElementById(inputId);
    const errEl    = document.getElementById(errId);
    const idExcluir = modo === 'editar' ? document.getElementById('ecat_id').value : null;

    if (!input.value.trim()) {
        errEl.textContent = 'El nombre de la categoría es obligatorio.';
        errEl.style.display = 'block';
        return false;
    }

    if (nombreCategoriaDuplicado(input.value, idExcluir)) {
        errEl.innerHTML = '<i class="fa-solid fa-triangle-exclamation"></i> Ya existe una categoría con este nombre. Verifica antes de crear una nueva.';
        errEl.style.display = 'block';
        return false;
    }

    errEl.style.display = 'none';
    return true;
};

// ══════════ VALIDACIÓN: EVENTOS SOLO CON FECHAS FUTURAS ══════════
function fechaEsPasada(valorFecha) {
    if (!valorFecha) return false;
    const hoy = new Date();
    hoy.setHours(0, 0, 0, 0);
    const fecha = new Date(valorFecha + 'T00:00:00');
    return fecha < hoy;
}

function validarFechaEventoForm(form) {
    const inicio = form.querySelector('input[name="fecha_inicio"]');
    const fin    = form.querySelector('input[name="fecha_fin"]');
    if (!inicio || !fin) return true;
    if (fechaEsPasada(inicio.value)) {
        alert('No se pueden programar eventos con fechas pasadas. Selecciona hoy o una fecha futura.');
        inicio.focus();
        return false;
    }
    if (fin.value && inicio.value && fin.value < inicio.value) {
        alert('La fecha de fin no puede ser anterior a la fecha de inicio.');
        fin.focus();
        return false;
    }
    return true;
}

document.addEventListener('DOMContentLoaded', function () {
    const hoyStr = new Date().toISOString().split('T')[0];

    // Fecha mínima = hoy en ambos formularios de evento (inicio y fin)
    const fCrearInicio  = document.querySelector('#modalCrearEvento input[name="fecha_inicio"]');
    const fCrearFin     = document.querySelector('#modalCrearEvento input[name="fecha_fin"]');
    const fEditarInicio = document.querySelector('#modalEditarEvento input[name="fecha_inicio"]');
    const fEditarFin    = document.querySelector('#modalEditarEvento input[name="fecha_fin"]');
    if (fCrearInicio)  fCrearInicio.min  = hoyStr;
    if (fCrearFin)     fCrearFin.min     = hoyStr;

    // Cuando cambie la fecha de inicio, la fecha de fin no puede ser anterior a ella
    [fCrearInicio, fEditarInicio].forEach(inicioInput => {
        if (!inicioInput) return;
        inicioInput.addEventListener('change', () => {
            const finInput = inicioInput.closest('form').querySelector('input[name="fecha_fin"]');
            if (finInput && inicioInput.value) {
                finInput.min = inicioInput.value > hoyStr ? inicioInput.value : hoyStr;
            }
        });
    });

    const formCrearEvento  = document.querySelector('#modalCrearEvento form');
    const formEditarEvento = document.getElementById('formEditarEvento');
    if (formCrearEvento)  formCrearEvento.addEventListener('submit', (e) => { if (!validarFechaEventoForm(formCrearEvento))  e.preventDefault(); });
    if (formEditarEvento) formEditarEvento.addEventListener('submit', (e) => { if (!validarFechaEventoForm(formEditarEvento)) e.preventDefault(); });
});

// ══════════ VALIDACIÓN: FECHAS DE REPORTES ══════════
// Envuelve las funciones generadoras de PDF (definidas en admin_dashboard.js)
// para asegurar que "desde" <= "hasta" y que ninguna sea futura, antes de generar el reporte.
function rangoFechasValido(desdeId, hastaId) {
    const desdeEl = document.getElementById(desdeId);
    const hastaEl = document.getElementById(hastaId);
    const desde = desdeEl.value;
    const hasta = hastaEl.value;
    const hoyStr = new Date().toISOString().split('T')[0];

    if (desde && desde > hoyStr) {
        alert('La fecha "desde" no puede ser futura.');
        return false;
    }
    if (hasta && hasta > hoyStr) {
        alert('La fecha "hasta" no puede ser futura.');
        return false;
    }
    if (desde && hasta && desde > hasta) {
        alert('La fecha "desde" no puede ser posterior a la fecha "hasta".');
        return false;
    }
    return true;
}

const _origGenerarDonaciones = window.generarReporteDonaciones;
window.generarReporteDonaciones = function () {
    if (!rangoFechasValido('rpt_don_desde', 'rpt_don_hasta')) return;
    if (typeof _origGenerarDonaciones === 'function') _origGenerarDonaciones();
};

const _origGenerarSolicitudes = window.generarReporteSolicitudes;
window.generarReporteSolicitudes = function () {
    if (!rangoFechasValido('rpt_sol_desde', 'rpt_sol_hasta')) return;
    if (typeof _origGenerarSolicitudes === 'function') _origGenerarSolicitudes();
};
// (El bloque que reabría el modal de categoría tras un error de Laravel ya no hace falta:
//  en Django el motivo del rechazo llega como mensaje.)

