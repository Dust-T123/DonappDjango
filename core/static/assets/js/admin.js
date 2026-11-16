// ── TABS ──────────────────────────────────────────────────────────────────
function switchTab() {
    const urlParams = new URLSearchParams(window.location.search);
    let hash = window.location.hash;

    if (!hash) {
        const tabParam = urlParams.get('tab');
        if (tabParam) {
            hash = '#' + tabParam;
        } else if (urlParams.get('don_search') || urlParams.get('don_estado') || urlParams.get('don_cat') ||
                   urlParams.get('sol_search') || urlParams.get('sol_estado') || urlParams.get('sol_cat')) {
            hash = '#donapp';
        } else if (urlParams.get('ev_search') || urlParams.get('ev_estado')) {
            hash = '#eventos';
        } else if (urlParams.get('cat_search')) {
            hash = '#categorias';
        } else if (urlParams.get('search') || urlParams.get('rol')) {
            hash = '#usuarios';
        } else {
            hash = '#dashboard';
        }
    }

    document.querySelectorAll('.tab-pane').forEach(p => p.classList.remove('active'));
    document.querySelectorAll('.nav-link').forEach(l => l.classList.remove('active'));

    const target  = document.querySelector(hash);
    const navItem = document.querySelector(`.nav-link[href="${hash}"]`);
    if (target)  target.classList.add('active');
    if (navItem) navItem.classList.add('active');
}

window.addEventListener('hashchange', switchTab);
window.addEventListener('load', switchTab);

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

// ── CREAR USUARIO ─────────────────────────────────────────────────────────
function abrirModalCrearUsuario() { abrirModal('modalCrearUsuario'); }

// ── EDITAR USUARIO ────────────────────────────────────────────────────────
function abrirModalEditarUsuario(u) {
    document.getElementById('eu_id').value      = u.idUsuario;
    document.getElementById('eu_nombre').value   = u.nombre;
    document.getElementById('eu_tipo').value     = u.tipoDocumento;
    document.getElementById('eu_doc').value      = u.numDocumento;
    document.getElementById('eu_fnac').value     = u.fechaNacimiento;
    document.getElementById('eu_dir').value      = u.direccion;
    document.getElementById('eu_email').value    = u.email;
    document.getElementById('eu_tel').value      = u.telefono;
    document.getElementById('eu_nec').value      = u.necesidad || '';
    if (document.getElementById('eu_prioridad'))  document.getElementById('eu_prioridad').value  = u.prioridad || '';
    if (document.getElementById('eu_obs_visita')) document.getElementById('eu_obs_visita').value = u.observacion_visita || '';
    document.getElementById('eu_rol').value      = u.rol;
    document.getElementById('eu_rol').dispatchEvent(new Event('change'));
    document.getElementById('eu_estado').value   = u.estado;
    document.getElementById('eu_pass').value     = '';
    document.getElementById('eu_pass2').value    = '';
    abrirModal('modalEditarUsuario');
}

// ── VALIDACIÓN OBSERVACIÓN AL RECHAZAR ────────────────────────────────────
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

// ── GESTIONAR DONACIÓN ────────────────────────────────────────────────────
function abrirModalDonacion(d) {
    document.getElementById('don_id').value     = d.idDonacion;
    document.getElementById('don_estado').value = d.estado;
    document.getElementById('don_obs').value    = d.observacion || '';
    actualizarHintObservacion('don_estado','don_obs_hint','don_obs','don_obs_err');

    const imagenHtml = d.imagen
        ? `<div class="modal-image-container"><img src="${d.imagen}" alt="Imagen Donación" class="img-preview"></div>`
        : `<div class="modal-image-container no-image"><i class="fa-solid fa-image-slash"></i> <p>Sin imagen</p></div>`;

    document.getElementById('don_detalle').innerHTML =
        `${imagenHtml}
         <div class="modal-info-text">
            <p><strong>Descripción:</strong> ${d.descripcion}</p>
            <p><strong>Categoría:</strong> ${d.categoria || '—'}</p>
            <p><strong>Stock:</strong> ${d.stock} &nbsp;|&nbsp; <strong>Fecha:</strong> ${d.fechaCreacion}</p>
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
        ? `<div class="modal-image-container"><img src="${s.imagen}" alt="Imagen Solicitud" class="img-preview"></div>`
        : `<div class="modal-image-container no-image"><i class="fa-solid fa-image-slash"></i> <p>Sin imagen</p></div>`;

    document.getElementById('sol_detalle').innerHTML =
        `${imagenHtml}
         <div class="modal-info-text">
            <p><strong>Descripción:</strong> ${s.descripcion}</p>
            <p><strong>Categoría:</strong> ${s.categoria || '—'}</p>
            <p><strong>Solicitante:</strong> ${s.solicitante || '—'} &nbsp;|&nbsp; <strong>Fecha:</strong> ${s.fechaCreacion}</p>
         </div>`;
    abrirModal('modalSolicitud');
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
        reader.onload = e => {
            preview.src           = e.target.result;
            preview.style.display = 'block';
        };
        reader.readAsDataURL(input.files[0]);
    } else {
        preview.style.display = 'none';
        preview.src = '';
    }
}

// ── OJO CONTRASEÑA ────────────────────────────────────────────────────────
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

// ── VALIDACIÓN CONTRASEÑAS ────────────────────────────────────────────────
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

function validarFormularioCompleto() {
    return validarPassPerfil();
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

    doc.setFontSize(16);
    doc.setTextColor(11, 90, 166);
    doc.text('DONAPP — Reporte de Donaciones', 14, 20);
    doc.setFontSize(10);
    doc.setTextColor(100);
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

    doc.setFontSize(16);
    doc.setTextColor(11, 90, 166);
    doc.text('DONAPP — Reporte de Solicitudes', 14, 20);
    doc.setFontSize(10);
    doc.setTextColor(100);
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

// ── CATEGORÍAS ────────────────────────────────────────────────────────────
function abrirModalEditarCategoria(cat) {
    document.getElementById('ecat_id').value     = cat.idCategoria;
    document.getElementById('ecat_nombre').value = cat.nombre;
    abrirModal('modalEditarCategoria');
}

function validarCategoria(modo) {
    const campo = modo === 'crear' ? 'cat_nombre'  : 'ecat_nombre';
    const errId = modo === 'crear' ? 'cat_err'     : 'ecat_err';
    const val   = document.getElementById(campo).value.trim();
    const err   = document.getElementById(errId);
    const regex = /^[A-Za-záéíóúÁÉÍÓÚñÑüÜ\s\(\)\-]+$/;
    if (val.length < 3)   { err.textContent = 'Mínimo 3 caracteres.'; err.style.display='block'; return false; }
    if (!regex.test(val)) { err.textContent = 'Solo letras y espacios, sin números.'; err.style.display='block'; return false; }
    err.style.display = 'none';
    return true;
}

function validarEntrada(input) {
    const errorId  = (input.id === 'cat_nombre') ? 'cat_err' : 'ecat_err';
    const errorMsg = document.getElementById(errorId);
    const valorLimpio = input.value.replace(/[^a-zA-ZáéíóúÁÉÍÓÚñÑ\s]/g, '');
    if (input.value !== valorLimpio) {
        input.value = valorLimpio;
        if (errorMsg) {
            errorMsg.innerText    = 'Solo se permiten letras y espacios.';
            errorMsg.style.display = 'block';
            setTimeout(() => { errorMsg.style.display = 'none'; }, 2000);
        }
    }
}

document.addEventListener('DOMContentLoaded', () => {
    ['cat_nombre', 'ecat_nombre'].forEach(id => {
        const el = document.getElementById(id);
        if (!el) return;
        el.addEventListener('input', function() {
            const pos     = this.selectionStart;
            const cleaned = this.value.replace(/[0-9]/g, '');
            if (this.value !== cleaned) {
                this.value = cleaned;
                this.setSelectionRange(pos - 1, pos - 1);
            }
        });
    });
});

// ── VALIDACIONES GLOBALES ─────────────────────────────────────────────────
document.querySelectorAll('input[name="nombre"]').forEach(inp => {
    if (inp.id !== 'edit_nombre') {
        inp.addEventListener('input', function() {
            const pos     = this.selectionStart;
            const cleaned = this.value.replace(/[0-9]/g, '');
            if (this.value !== cleaned) {
                this.value = cleaned;
                this.setSelectionRange(pos - 1, pos - 1);
            }
        });
    }
});

document.querySelectorAll('input[name="numDocumento"]').forEach(inp => {
    inp.addEventListener('input', function() {
        this.value = this.value.replace(/\D/g, '').slice(0, 15);
    });
});

document.querySelectorAll('input[name="telefono"]').forEach(inp => {
    inp.addEventListener('input', function() {
        this.value = this.value.replace(/\D/g, '').slice(0, 10);
    });
});

document.querySelectorAll('input[type="password"]').forEach(inp => {
    inp.addEventListener('input', function() {
        this.style.borderColor = (this.value.length > 0 && this.value.length < 6) ? '#e53935' : '';
    });
});

// ── CAMPO NECESIDAD / PRIORIDAD SEGÚN ROL ─────────────────────────────────
function gestionarCampoNecesidad(rolSelectId, necesidadInputId, prioridadGroupId) {
    const rolSelect      = document.getElementById(rolSelectId);
    const necesidadInput = document.getElementById(necesidadInputId);
    const prioridadGroup = prioridadGroupId ? document.getElementById(prioridadGroupId) : null;

    if (!rolSelect || !necesidadInput) return;

    const actualizar = () => {
        const esAdmin = rolSelect.value === 'administrador' || rolSelect.value === 'asistente';
        if (esAdmin) {
            necesidadInput.value       = '';
            necesidadInput.placeholder = 'No aplica para este rol';
            necesidadInput.disabled    = true;
            necesidadInput.required    = false;
            if (prioridadGroup) prioridadGroup.style.display = 'none';
            const obsGroup = document.getElementById(prioridadGroupId ? prioridadGroupId.replace('prioridad','obs') : '');
            if (obsGroup) obsGroup.style.display = 'none';
        } else {
            necesidadInput.disabled    = false;
            necesidadInput.placeholder = 'Ingrese la necesidad del donante/solicitante';
            if (prioridadGroup) prioridadGroup.style.display = '';
            const obsGroup2 = document.getElementById(prioridadGroupId ? prioridadGroupId.replace('prioridad','obs') : '');
            if (obsGroup2) obsGroup2.style.display = '';
        }
    };

    rolSelect.addEventListener('change', actualizar);
    actualizar();
}

document.addEventListener('DOMContentLoaded', () => {
    gestionarCampoNecesidad('nuevo_rol', 'nuevo_necesidad', 'grp_nuevo_prioridad');
    gestionarCampoNecesidad('eu_rol', 'eu_nec', 'grp_eu_prioridad');
});

function activarTab(tabId) {
    console.log('Cambiando a: ' + tabId);
}
