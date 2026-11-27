// Escapa texto del usuario antes de insertarlo con innerHTML (evita XSS almacenado).

// Lógica del panel del asistente que en Laravel vivía en un <script> dentro del Blade.
// Las URLs llegan desde el template en window.ROUTES_ASIS (ver dashboard_asistente.html).
const ROUTES_ASIS = window.ROUTES_ASIS;

function abrirModalVisita(v) {
    const editable = !!v.editable;
    const form = document.getElementById('formVisita');
    const estadoSel = document.getElementById('vis_estado');
    const obsField = document.getElementById('vis_obs');

    form.action = editable ? ROUTES_ASIS.visita(v.idVisita) : ROUTES_ASIS.visitaNota(v.idVisita);

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

    document.getElementById('vis_detalle').innerHTML = detalleVisitaHtml(v);

    const hist = v.historial || [];
    document.getElementById('vis_historial').innerHTML = hist.length
        ? hist.map(h => `
            <div class="bitacora-item">
                <div class="bitacora-meta"><strong>${esc(h.autor)}</strong> · ${esc(h.fecha)}</div>
                <div class="bitacora-texto">${esc(h.texto)}</div>
            </div>`).join('')
        : '<p class="text-muted" style="font-size:0.85rem">Aún no hay notas en la bitácora.</p>';

    abrirModal('modalVisita');
}

let _donanteActivo = null;

// ── Donación ──────────────────────────────────────────────────
const _origDon = window.abrirModalDonacion;
window.abrirModalDonacion = function(d) {
    if (_origDon) _origDon(d);
    document.getElementById('formDonacion').action = ROUTES_ASIS.donacion(d.idDonacion);
    document.getElementById('don_id').value = d.idDonacion;
};

// ── Solicitud ─────────────────────────────────────────────────
const _origSol = window.abrirModalSolicitud;
window.abrirModalSolicitud = function(s) {
    if (_origSol) _origSol(s);
    document.getElementById('formSolicitud').action = ROUTES_ASIS.solicitud(s.idSolicitud);
    document.getElementById('sol_id').value = s.idSolicitud;
};

// ── Categoría ─────────────────────────────────────────────────
const _origEditCat = window.abrirModalEditarCategoria;
window.abrirModalEditarCategoria = function(c) {
    if (_origEditCat) _origEditCat(c);
    document.getElementById('formEditarCategoria').action = ROUTES_ASIS.editarCategoria(c.idCategoria);
    document.getElementById('edit_cat_id').value   = c.idCategoria;
    document.getElementById('edit_cat_nombre').value = c.nombre;
    abrirModal('modalEditarCategoria');
};

// ── Evento ────────────────────────────────────────────────────
const _origEditEvt = window.abrirModalEditarEvento;
window.abrirModalEditarEvento = function(ev) {
    if (_origEditEvt) _origEditEvt(ev);
    document.getElementById('formEditarEvento').action = ROUTES_ASIS.editarEvento(ev.idEvento);
};

// ── Editar donante ────────────────────────────────────────────
window.abrirModalEditarDonante = function(cli) {
    _donanteActivo = cli;
    document.getElementById('formEditarDonante').action      = ROUTES_ASIS.editarDonante(cli.idUsuario);
    document.getElementById('edit_cli_nombre').value         = cli.nombre            ?? '';
    document.getElementById('edit_cli_apellido').value       = cli.apellido          ?? '';
    document.getElementById('edit_cli_tipoDoc').value        = cli.tipoDocumento      ?? '';
    document.getElementById('edit_cli_numDoc').value         = cli.numDocumento       ?? '';
    document.getElementById('edit_cli_fechaNac').value       = cli.fechaNacimiento    ?? '';
    document.getElementById('edit_cli_email').value          = cli.email              ?? '';
    document.getElementById('edit_cli_telefono').value       = cli.telefono           ?? '';
    document.getElementById('edit_cli_direccion').value      = cli.direccion          ?? '';
    document.getElementById('edit_cli_necesidad').value      = cli.necesidad          ?? '';
    document.getElementById('edit_cli_prioridad').value      = cli.prioridad          ?? '';
    document.getElementById('edit_cli_obs').value            = cli.observacion_visita ?? '';
    abrirModal('modalEditarDonante');
};

// ── Solicitar corrección de datos sensibles de un donante ─────
window.abrirModalCorreccionDonante = function() {
    if (!_donanteActivo) return;
    document.getElementById('cc_nombre_donante').textContent = _donanteActivo.nombre ?? '';
    document.getElementById('formCorreccionDonante').action  = ROUTES_ASIS.solicitarCorreccionDonante(_donanteActivo.idUsuario);
    document.getElementById('formCorreccionDonante').reset();
    cerrarModal('modalEditarDonante');
    abrirModal('modalCorreccionDonante');
};

// ── Historial de donaciones / solicitudes del donante ─────────
window.abrirModalHistorialDonante = async function(cli) {
    document.getElementById('historial_nombre').textContent = cli.nombre;
    document.getElementById('historial_cuerpo').innerHTML   = '<p class="text-muted"><i class="fa-solid fa-spinner fa-spin"></i> Cargando...</p>';
    abrirModal('modalHistorialDonante');

    try {
        const res  = await fetch(ROUTES_ASIS.historialDonante(cli.idUsuario));

        if (!res.ok) throw new Error('Error al obtener el historial.');

        const data = await res.json();

        const donRows = data.donaciones && data.donaciones.length
            ? data.donaciones.map(d => `
                <tr>
                    <td>${d.idDonacion}</td>
                    <td class="td-desc">${esc(d.descripcion ?? '—')}</td>
                    <td class="td-cat">${esc(d.categoria   ?? '—')}</td>
                    <td><span class="badge estado-${esc(d.estado)}">${esc(d.estado)}</span></td>
                    <td>${d.fecha       ?? '—'}</td>
                </tr>`).join('')
            : `<tr><td colspan="5" class="empty-row">Sin donaciones registradas.</td></tr>`;

        const solRows = data.solicitudes && data.solicitudes.length
            ? data.solicitudes.map(s => `
                <tr>
                    <td>${s.idSolicitud}</td>
                    <td class="td-desc">${esc(s.descripcion ?? '—')}</td>
                    <td class="td-cat">${esc(s.categoria   ?? '—')}</td>
                    <td><span class="badge estado-${esc(s.estado)}">${esc(s.estado)}</span></td>
                    <td>${s.fecha       ?? '—'}</td>
                </tr>`).join('')
            : `<tr><td colspan="5" class="empty-row">Sin solicitudes registradas.</td></tr>`;

        document.getElementById('historial_cuerpo').innerHTML = `
            <h4 style="margin-bottom:8px"><i class="fa-solid fa-box-open"></i> Donaciones</h4>
            <div class="table-wrap" style="margin-bottom:20px">
                <table>
                    <thead>
                        <tr><th>#</th><th>Descripción</th><th>Categoría</th><th>Estado</th><th>Fecha</th></tr>
                    </thead>
                    <tbody>${donRows}</tbody>
                </table>
            </div>
            <h4 style="margin-bottom:8px"><i class="fa-solid fa-clipboard-list"></i> Solicitudes</h4>
            <div class="table-wrap">
                <table>
                    <thead>
                        <tr><th>#</th><th>Descripción</th><th>Categoría</th><th>Estado</th><th>Fecha</th></tr>
                    </thead>
                    <tbody>${solRows}</tbody>
                </table>
            </div>`;
    } catch (e) {
        document.getElementById('historial_cuerpo').innerHTML =
            `<p style="color:red"><i class="fa-solid fa-triangle-exclamation"></i> Error al cargar el historial. Intenta de nuevo.</p>`;
    }
};
// ── VALIDACIÓN FECHAS DE EVENTOS ─────────────────────────────
document.addEventListener('DOMContentLoaded', function () {
    const hoyStr = new Date().toISOString().split('T')[0];

    // Fecha mínima = hoy en ambos formularios
    const fCrear       = document.querySelector('#modalCrearEvento input[name="fecha_inicio"]');
    const fCrearFin    = document.querySelector('#modalCrearEvento input[name="fecha_fin"]');
    const fEditarInicio= document.querySelector('#modalEditarEvento input[name="fecha_inicio"]');
    if (fCrear)    fCrear.min    = hoyStr;
    if (fCrearFin) fCrearFin.min = hoyStr;

    // Cuando cambie la fecha de inicio, la de fin no puede quedar antes que ella
    [fCrear, fEditarInicio].forEach(inicioInput => {
        if (!inicioInput) return;
        inicioInput.addEventListener('change', () => {
            const finInput = inicioInput.closest('form').querySelector('input[name="fecha_fin"]');
            if (finInput && inicioInput.value) {
                finInput.min = inicioInput.value > hoyStr ? inicioInput.value : hoyStr;
            }
        });
    });

    // Validar antes de enviar
    const formCrear  = document.querySelector('#modalCrearEvento form');
    const formEditar = document.getElementById('formEditarEvento');

    function fechaEsPasada(valor) {
        if (!valor) return false;
        const hoy = new Date(); hoy.setHours(0,0,0,0);
        return new Date(valor + 'T00:00:00') < hoy;
    }

    function validarFechaEvento(form) {
        const inicio = form.querySelector('input[name="fecha_inicio"]');
        const fin    = form.querySelector('input[name="fecha_fin"]');
        if (inicio && fechaEsPasada(inicio.value)) {
            alert('No se pueden programar eventos con fechas pasadas. Selecciona hoy o una fecha futura.');
            inicio.focus();
            return false;
        }
        if (inicio && fin && fin.value && inicio.value && fin.value < inicio.value) {
            alert('La fecha de fin no puede ser anterior a la fecha de inicio.');
            fin.focus();
            return false;
        }
        return true;
    }

    if (formCrear)  formCrear.addEventListener('submit',  e => { if (!validarFechaEvento(formCrear))  e.preventDefault(); });
    if (formEditar) formEditar.addEventListener('submit', e => { if (!validarFechaEvento(formEditar)) e.preventDefault(); });
});

// ══════════ VALIDACIÓN: CATEGORÍAS DUPLICADAS (donante) ══════════
// El backend SIEMPRE valida de nuevo (unique + regex en AsisController); esto
// solo evita un viaje al servidor innecesario y da feedback inmediato.
function categoriasExistentesListAsis() {
    const el = document.getElementById('categoriasExistentesAsis');
    if (!el) return [];
    try { return JSON.parse(el.textContent); } catch (e) { return []; }
}

function nombreCategoriaDuplicadoAsis(nombre, idExcluir = null) {
    const normalizado = nombre.trim().toLowerCase();
    return categoriasExistentesListAsis().some(c =>
        c.nombre === normalizado && (idExcluir === null || String(c.id) !== String(idExcluir))
    );
}

window.validarCategoriaAsistente = function(input) {
    const esEdicion = input.id === 'edit_cat_nombre';
    const errEl      = document.getElementById(esEdicion ? 'edit_cat_err' : 'asis_cat_err');
    const idExcluir  = esEdicion ? document.getElementById('edit_cat_id').value : null;

    if (!input.value.trim()) {
        errEl.textContent = 'El nombre de la categoría es obligatorio.';
        errEl.style.display = 'block';
        return false;
    }
    if (nombreCategoriaDuplicadoAsis(input.value, idExcluir)) {
        errEl.innerHTML = '<i class="fa-solid fa-triangle-exclamation"></i> Ya existe una categoría con este nombre. Verifica antes de guardar.';
        errEl.style.display = 'block';
        return false;
    }
    errEl.style.display = 'none';
    return true;
};

// ══════════ VALIDACIÓN: FECHAS DE REPORTES ══════════
// Envuelve las funciones generadoras de PDF (definidas en asistente.js) para
// asegurar que "desde" <= "hasta" y que ninguna sea futura, antes de generar.
function rangoFechasValidoAsis(desdeId, hastaId) {
    const desde = document.getElementById(desdeId).value;
    const hasta = document.getElementById(hastaId).value;
    const hoyStr = new Date().toISOString().split('T')[0];

    if (desde && desde > hoyStr) { alert('La fecha "desde" no puede ser futura.'); return false; }
    if (hasta && hasta > hoyStr) { alert('La fecha "hasta" no puede ser futura.'); return false; }
    if (desde && hasta && desde > hasta) { alert('La fecha "desde" no puede ser posterior a la fecha "hasta".'); return false; }
    return true;
}

const _origGenerarDonacionesAsis = window.generarReporteDonaciones;
window.generarReporteDonaciones = function () {
    if (!rangoFechasValidoAsis('rpt_don_desde', 'rpt_don_hasta')) return;
    if (typeof _origGenerarDonacionesAsis === 'function') _origGenerarDonacionesAsis();
};

const _origGenerarSolicitudesAsis = window.generarReporteSolicitudes;
window.generarReporteSolicitudes = function () {
    if (!rangoFechasValidoAsis('rpt_sol_desde', 'rpt_sol_hasta')) return;
    if (typeof _origGenerarSolicitudesAsis === 'function') _origGenerarSolicitudesAsis();
};
