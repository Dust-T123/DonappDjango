// Escapa texto del usuario antes de insertarlo con innerHTML (evita XSS almacenado).
function esc(v) {
    return String(v ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
}

// ── VALIDACIÓN: solo letras y espacios (bloquea la tecla, no solo limpia después) ──
function soloLetras(e) {
    const key   = e.key || String.fromCharCode(e.keyCode || e.which);
    const letras = /^[a-zA-ZáéíóúÁÉÍÓÚñÑüÜ\s]$/;
    return letras.test(key);
}

// ── TABS ──────────────────────────────────────────────────────────────────
function mostrarTab(tabId) {
    document.querySelectorAll('.tab-pane').forEach(p => p.classList.remove('active'));
    document.querySelectorAll('.nav-link').forEach(l => l.classList.remove('active'));

    const pane    = document.getElementById(tabId);
const navLink = document.querySelector(`.nav-link[href="#${tabId}"]`);
    if (pane)    pane.classList.add('active');
    if (navLink) navLink.classList.add('active');
}

function irTab(tabId, e) {
    e.preventDefault();
    history.pushState({}, '', '#' + tabId);
    mostrarTab(tabId);
}

function initTabs() {
    const urlParams = new URLSearchParams(window.location.search);
    const tabParam  = urlParams.get('tab');
    const hash      = window.location.hash.replace('#', '');

    let tabId = 'dashboard';

    if (tabParam && document.getElementById(tabParam)) {
        tabId = tabParam;
    } else if (hash && document.getElementById(hash)) {
        tabId = hash;
    } else {
        if (urlParams.get('don_search') || urlParams.get('don_estado') || urlParams.get('don_cat') ||
            urlParams.get('sol_search') || urlParams.get('sol_estado') || urlParams.get('sol_cat') ||
            urlParams.get('don_sort')   || urlParams.get('sol_sort'))   tabId = 'donapp';
        if (urlParams.get('ev_search')  || urlParams.get('ev_estado')  || urlParams.get('ev_sort'))  tabId = 'eventos';
        if (urlParams.get('cli_search') || urlParams.get('cli_sort')   || urlParams.get('cli_prioridad')) tabId = 'donantes';
        if (urlParams.get('cat_search') || urlParams.get('cat_sort'))   tabId = 'categorias';
    }

    mostrarTab(tabId);
}

function activarTab(hash) {
    const tabId = hash.replace('#', '');
    history.pushState({}, '', '#' + tabId);
    mostrarTab(tabId);
}

window.addEventListener('load', initTabs);
window.addEventListener('popstate', initTabs);

// Los <a href="#tabid" class="nav-link"> nunca tenían un listener real de click
// (solo cambiaban el hash de la URL sin togglear la clase .active). Por eso
// después de recargar con filtros (que sí activan la pestaña correcta vía
// initTabs), un clic normal en otra pestaña no hacía nada — parecía "trabado".
document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('.nav-link[href^="#"]').forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            const tabId = link.getAttribute('href').replace('#', '');
            activarTab(tabId);
        });
    });
});

// ── INNER TABS ────────────────────────────────────────────────────────────
function switchInner(btn, panelId) {
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.inner-panel').forEach(p => p.style.display = 'none');
    btn.classList.add('active');
    document.getElementById(panelId).style.display = 'block';
}

document.addEventListener('DOMContentLoaded', () => {
    const params = new URLSearchParams(window.location.search);
    if (params.get('sol_search') || params.get('sol_estado') || params.get('sol_cat')) {
        const solBtn = document.querySelector('.tab-btn[onclick*="sol-panel"]');
        if (solBtn) switchInner(solBtn, 'sol-panel');
    }
});

// ── MODALES ───────────────────────────────────────────────────────────────
function abrirModal(id)  { document.getElementById(id).style.display = 'flex'; }
function cerrarModal(id) { document.getElementById(id).style.display = 'none'; }

document.querySelectorAll('.modal').forEach(m => {
    m.addEventListener('click', e => { if (e.target === m) cerrarModal(m.id); });
});

// ── VER DONANTE ───────────────────────────────────────────────────────────
function abrirModalVerDonante(cli) {
    const estadoClass = cli.estado === 'activo' ? 'estado-activo' : `estado-${cli.estado}`;
    const estadoLabel = cli.estado ? cli.estado.charAt(0).toUpperCase() + cli.estado.slice(1) : '—';

    const fila = (icon, label, valor) =>
        `<div class="detalle-fila">
            <i class="fa-solid fa-${icon} detalle-icon"></i>
            <div class="detalle-label">${label}</div>
            <div class="detalle-valor">${esc(valor)}</div>
        </div>`;

    document.getElementById('donante_detalle').innerHTML =
        fila('user',                   'Nombre',       cli.nombre || '—') +
        fila('id-card',                'Documento',    `${cli.tipoDocumento}: ${cli.numDocumento}`) +
        fila('envelope',               'Email',         cli.email || '—') +
        fila('phone',                  'Teléfono',     cli.telefono || '—') +
        fila('location-dot',           'Dirección',    cli.direccion || '—') +
        fila('cake-candles',           'Nacimiento',   cli.fechaNacimiento || '—') +
        fila('heart-pulse',            'Necesidad',    cli.necesidad || '—') +
        fila('triangle-exclamation',   'Prioridad',    cli.prioridad || '—') +
        fila('clipboard',              'Obs. visita',  cli.observacion_visita || '—') +
        `<div class="detalle-fila">
            <i class="fa-solid fa-circle-check detalle-icon"></i>
            <div class="detalle-label">Estado</div>
            <div class="detalle-valor"><span class="badge ${esc(estadoClass)}">${esc(estadoLabel)}</span></div>
        </div>`;

    abrirModal('modalVerDonante');
}

// ── FILTRAR SOLICITUDES POR DONANTE ──────────────────────────────────────
function filtrarSolicitudesPorDonante(nombre) {
    activarTab('#donapp');
    setTimeout(() => {
        const solBtn = document.querySelector('.tab-btn[onclick*="sol-panel"]');
        if (solBtn) switchInner(solBtn, 'sol-panel');
    }, 100);
    setTimeout(() => {
        const input = document.querySelector('input[name="sol_search"]');
        if (input) {
            input.value = nombre;
            input.closest('form').submit();
        }
    }, 200);
    return false;
}

// ── GESTIONAR DONACIÓN ────────────────────────────────────────────────────
function formatearFecha(fechaStr) {
    if (!fechaStr) return '—';
    const partes = String(fechaStr).substring(0, 10).split('-');
    if (partes.length === 3) return `${partes[2]}/${partes[1]}/${partes[0]}`;
    return fechaStr;
}
function abrirModalDonacion(d) {
    document.getElementById('don_id').value     = d.idDonacion;
    document.getElementById('don_estado').value = d.estado;
    document.getElementById('don_obs').value    = d.observacion || '';
    actualizarHintObservacion('don_estado','don_obs_hint','don_obs','don_obs_err');

    const imagenHtml = d.imagen
        ? `<div class="modal-image-container"><img src="${esc(d.imagen)}" alt="Imagen Donación" class="img-preview"></div>`
        : `<div class="modal-image-container no-image"><i class="fa-solid fa-image-slash"></i> <p>Sin imagen</p></div>`;

    document.getElementById('don_detalle').innerHTML =
        `${imagenHtml}
         <div class="modal-info-text">
            <p><strong>Descripción:</strong> ${esc(d.descripcion)}</p>
            <p><strong>Categoría:</strong> ${esc(d.categoria || '—')}</p>
            <p><strong>Stock:</strong> ${d.stock} &nbsp;|&nbsp; <strong>Fecha:</strong> ${formatearFecha(d.fechaCreacion)}</p>
         </div>`;
    abrirModal('modalDonacion');
}

// ── GESTIONAR SOLICITUD ───────────────────────────────────────────────────
function abrirModalSolicitud(s) {
    document.getElementById('sol_id').value     = s.idSolicitud;
    document.getElementById('sol_estado').value = s.estado;
    document.getElementById('sol_obs').value    = s.observacion || '';
    actualizarHintObservacion('sol_estado','sol_obs_hint','sol_obs','sol_obs_err');

    const imagenHtml = s.imagen
        ? `<div class="modal-image-container"><img src="${esc(s.imagen)}" alt="Imagen Solicitud" class="img-preview"></div>`
        : `<div class="modal-image-container no-image"><i class="fa-solid fa-image-slash"></i> <p>Sin imagen</p></div>`;

    document.getElementById('sol_detalle').innerHTML =
        `${imagenHtml}
         <div class="modal-info-text">
            <p><strong>Descripción:</strong> ${esc(s.descripcion)}</p>
            <p><strong>Categoría:</strong> ${esc(s.categoria || '—')}</p>
           <p><strong>Solicitante:</strong> ${esc(s.solicitante || '—')} &nbsp;|&nbsp; <strong>Fecha:</strong> ${formatearFecha(s.fechaCreacion)}</p>
         </div>`;
    abrirModal('modalSolicitud');
}

// ── EDITAR DONANTE ────────────────────────────────────────────────────────
function abrirModalEditarDonante(cli) {
    document.getElementById('edit_cli_id').value        = cli.idUsuario;
    document.getElementById('edit_cli_nombre').value    = cli.nombre;
    document.getElementById('edit_cli_tipoDoc').value   = cli.tipoDocumento;
    document.getElementById('edit_cli_numDoc').value    = cli.numDocumento;
    document.getElementById('edit_cli_fechaNac').value  = cli.fechaNacimiento;
    document.getElementById('edit_cli_email').value     = cli.email;
    document.getElementById('edit_cli_telefono').value  = cli.telefono;
    document.getElementById('edit_cli_direccion').value = cli.direccion;
    document.getElementById('edit_cli_necesidad').value = cli.necesidad || '';
    if (document.getElementById('edit_cli_prioridad')) document.getElementById('edit_cli_prioridad').value = cli.prioridad || '';
    if (document.getElementById('edit_cli_obs'))       document.getElementById('edit_cli_obs').value       = cli.observacion_visita || '';
    document.getElementById('edit_cli_pass').value      = '';
    document.getElementById('edit_cli_pass2').value     = '';
    document.getElementById('edit_cli_pass_err').style.display = 'none';
    abrirModal('modalEditarDonante');
}

// ── CATEGORÍAS ────────────────────────────────────────────────────────────
function abrirModalEditarCategoria(cat) {
    document.getElementById('edit_cat_id').value     = cat.idCategoria;
    document.getElementById('edit_cat_nombre').value = cat.nombre;
    abrirModal('modalEditarCategoria');
}

// ── EVENTOS ───────────────────────────────────────────────────────────────
function abrirModalCrearEvento() { abrirModal('modalCrearEvento'); }

function abrirModalEditarEvento(evento) {
    document.getElementById('edit_idEvento').value      = evento.idEvento;
    document.getElementById('edit_nombre').value        = evento.Nombre || evento.nombre || '';
    document.getElementById('edit_estado').value        = evento.estado;
    document.getElementById('edit_fecha_inicio').value  = evento.fecha_inicio || '';
    document.getElementById('edit_fecha_fin').value     = evento.fecha_fin || '';
    document.getElementById('edit_lugar_entrega').value = evento.lugar_entrega || '';
    document.getElementById('edit_titulo_pub').value    = evento.titulo_pub || '';
    document.getElementById('edit_contenido_pub').value = evento.contenido_pub || '';

    // Solo bloqueamos fechas pasadas si el evento aún no terminó.
    const hoyStr = new Date().toISOString().split('T')[0];
    const finInput = document.getElementById('edit_fecha_fin');
    finInput.min = (evento.fecha_fin && evento.fecha_fin < hoyStr) ? '' : hoyStr;

    document.getElementById('edit_imagen_pub').value = '';
    const nuevaPreview = document.getElementById('edit_nueva_img_preview');
    nuevaPreview.style.display = 'none';
    nuevaPreview.src = '';

    const previewWrap = document.getElementById('edit_img_preview_wrap');
    const previewImg  = document.getElementById('edit_img_preview');
    if (evento.imagen && evento.imagen.trim() !== '') {
        previewImg.src            = evento.imagen;
        previewWrap.style.display = 'block';
    } else {
        previewWrap.style.display = 'none';
        previewImg.src = '';
    }
    abrirModal('modalEditarEvento');
}

function previewNuevaImagen(input) {
    const preview = document.getElementById('edit_nueva_img_preview');
    if (input.files && input.files[0]) {
        const reader = new FileReader();
        reader.onload = e => { preview.src = e.target.result; preview.style.display = 'block'; };
        reader.readAsDataURL(input.files[0]);
    } else {
        preview.style.display = 'none';
        preview.src = '';
    }
}

// ── VALIDACIONES ──────────────────────────────────────────────────────────
function actualizarHintObservacion(selectId, hintId, obsId, errId) {
    const estado = document.getElementById(selectId).value;
    const hint   = document.getElementById(hintId);
    const obs    = document.getElementById(obsId);
    const err    = document.getElementById(errId);
    if (estado === 'rechazada') {
        hint.textContent      = '(obligatoria al rechazar)';
        hint.style.color      = '#c62828';
        obs.style.borderColor = '#c62828';
    } else {
        hint.textContent      = '(opcional)';
        hint.style.color      = '';
        obs.style.borderColor = '';
        if (err) err.style.display = 'none';
    }
}

function validarObservacionRequerida(selectId, obsId, errId) {
    const estado = document.getElementById(selectId).value;
    const obs    = document.getElementById(obsId).value.trim();
    const err    = document.getElementById(errId);
    if (estado === 'rechazada' && obs === '') {
        err.style.display = 'block';
        document.getElementById(obsId).focus();
        return false;
    }
    if (err) err.style.display = 'none';
    return true;
}

function togglePass(inputId, iconId) {
    const inp  = document.getElementById(inputId);
    const icon = document.getElementById(iconId);
    if (inp.type === 'password') {
        inp.type       = 'text';
        icon.className = 'fa-solid fa-eye-slash';
    } else {
        inp.type       = 'password';
        icon.className = 'fa-solid fa-eye';
    }
}

function validarPassModal(p1Id, p2Id, errId) {
    const p1  = document.getElementById(p1Id).value;
    const p2  = document.getElementById(p2Id).value;
    const err = document.getElementById(errId);
    if (!p1 && !p2) { err.style.display = 'none'; return true; }
    if (p1.length > 0 && p1.length < 6) {
        err.textContent   = 'La contraseña debe tener al menos 6 caracteres.';
        err.style.display = 'block';
        return false;
    }
    if (p1 !== p2) {
        err.textContent   = 'Las contraseñas no coinciden.';
        err.style.display = 'block';
        return false;
    }
    err.style.display = 'none';
    return true;
}

function validarPassPerfil() {
    return validarPassModal('perfil_pass','perfil_pass2','perfil_pass_err');
}

// ── FLASH MSG ─────────────────────────────────────────────────────────────
const flash = document.getElementById('flashMsg');
if (flash) setTimeout(() => flash.style.opacity = '0', 3000);

const flashNotif = document.getElementById('flashNotif');
if (flashNotif) setTimeout(() => flashNotif.style.opacity = '0', 4000);

// ── REPORTES PDF ──────────────────────────────────────────────────────────
const donacionesData  = JSON.parse(document.getElementById('donacionesData').textContent);
const solicitudesData = JSON.parse(document.getElementById('solicitudesData').textContent);

function filtrarPorCriterios(data, estadoId, desdeId, hastaId) {
    const estado = document.getElementById(estadoId).value;
    const desde  = document.getElementById(desdeId).value;
    const hasta  = document.getElementById(hastaId).value;
    return data.filter(item => {
        const itemDate = item.fechaCreacion ? item.fechaCreacion.substring(0,10) : '';
        if (estado !== 'todos' && item.estado !== estado) return false;
        if (desde && itemDate < desde) return false;
        if (hasta && itemDate > hasta) return false;
        return true;
    });
}

function generarReporteDonaciones() {
    const { jsPDF } = window.jspdf;
    const doc    = new jsPDF();
    const datos  = filtrarPorCriterios(donacionesData, 'rpt_don_estado', 'rpt_don_desde', 'rpt_don_hasta');
    const estado = document.getElementById('rpt_don_estado').value;
    const hoy    = new Date().toLocaleDateString('es-CO');

    doc.setFontSize(16); doc.setTextColor(11, 90, 166);
    doc.text('DONAPP — Reporte de Donaciones', 14, 20);
    doc.setFontSize(10); doc.setTextColor(100);
    doc.text(`Filtro: ${estado} | Generado: ${hoy}`, 14, 28);

    if (datos.length === 0) {
        doc.setTextColor(150);
        doc.text('No hay registros con los criterios seleccionados.', 14, 45);
    } else {
        doc.autoTable({
            startY: 35,
            head: [['#', 'Descripción', 'Categoría', 'Stock', 'Estado', 'Donante', 'Fecha', 'Observación']],
            body: datos.map(d => [
                d.idDonacion, d.descripcion, d.categoria || '—', d.stock,
                d.estado, d.donante || '—',
                d.fechaCreacion ? d.fechaCreacion.substring(0,10) : '—',
                d.observacion || '—'
            ]),
            styles:             { fontSize: 8 },
            headStyles:         { fillColor: [11, 90, 166] },
            alternateRowStyles: { fillColor: [227, 237, 251] }
        });
    }
    doc.save(`reporte_donaciones_${Date.now()}.pdf`);
}

function generarReporteSolicitudes() {
    const { jsPDF } = window.jspdf;
    const doc    = new jsPDF();
    const datos  = filtrarPorCriterios(solicitudesData, 'rpt_sol_estado', 'rpt_sol_desde', 'rpt_sol_hasta');
    const estado = document.getElementById('rpt_sol_estado').value;
    const hoy    = new Date().toLocaleDateString('es-CO');

    doc.setFontSize(16); doc.setTextColor(11, 90, 166);
    doc.text('DONAPP — Reporte de Solicitudes', 14, 20);
    doc.setFontSize(10); doc.setTextColor(100);
    doc.text(`Filtro: ${estado} | Generado: ${hoy}`, 14, 28);

    if (datos.length === 0) {
        doc.setTextColor(150);
        doc.text('No hay registros con los criterios seleccionados.', 14, 45);
    } else {
        doc.autoTable({
            startY: 35,
            head: [['#', 'Descripción', 'Categoría', 'Estado', 'Solicitante', 'Fecha', 'Observación']],
            body: datos.map(s => [
                s.idSolicitud, s.descripcion, s.categoria || '—',
                s.estado, s.solicitante || '—',
                s.fechaCreacion ? s.fechaCreacion.substring(0,10) : '—',
                s.observacion || '—'
            ]),
            styles:             { fontSize: 8 },
            headStyles:         { fillColor: [11, 90, 166] },
            alternateRowStyles: { fillColor: [227, 237, 251] }
        });
    }
    doc.save(`reporte_solicitudes_${Date.now()}.pdf`);
}

// ── VALIDACIÓN CATEGORÍAS ─────────────────────────────────────────────────
function validarCategoriaAsistente(input) {
    const errorId  = (input.id === 'asis_cat_nombre') ? 'asis_cat_err' : 'edit_cat_err';
    const errorMsg = document.getElementById(errorId);
    const valorLimpio = input.value.replace(/[^a-zA-ZáéíóúÁÉÍÓÚñÑüÜ\s\-(),:.]/g, '');
    if (input.value !== valorLimpio) {
        input.value = valorLimpio;
        if (errorMsg) {
            errorMsg.innerText    = 'Solo se permiten letras, espacios y - ( ) , : .';
            errorMsg.style.display = 'block';
            setTimeout(() => { errorMsg.style.display = 'none'; }, 2000);
        }
    }
}
