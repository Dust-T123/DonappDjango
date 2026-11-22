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

document.addEventListener('DOMContentLoaded', () => {
    const params = new URLSearchParams(window.location.search);
    if (params.get('sol_search') || params.get('sol_estado') || params.get('sol_cat')) {
        const solBtn = document.querySelector('.tab-btn[onclick*="sol-panel"]');
        if (solBtn) switchInner(solBtn, 'sol-panel');
    }
});

// ── MODALES ───────────────────────────────────────────────────────────────

document.querySelectorAll('.modal').forEach(m => {
    m.addEventListener('click', e => { if (e.target === m) cerrarModal(m.id); });
});

// ── CREAR USUARIO ─────────────────────────────────────────────────────────

// ── EDITAR USUARIO ────────────────────────────────────────────────────────

// ── VALIDACIÓN OBSERVACIÓN AL RECHAZAR ────────────────────────────────────

// ── GESTIONAR DONACIÓN ────────────────────────────────────────────────────

// ── GESTIONAR SOLICITUD ───────────────────────────────────────────────────

// ── EVENTOS ───────────────────────────────────────────────────────────────

// ── OJO CONTRASEÑA ────────────────────────────────────────────────────────

// ── VALIDACIÓN CONTRASEÑAS ────────────────────────────────────────────────

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

// ── CATEGORÍAS ────────────────────────────────────────────────────────────

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
// nombre, apellido, teléfono y documento los valida validaciones.js.

// numDocumento: lo valida validaciones.js (letras y números, 4-15, mayúsculas).
// Aquí antes se borraban las letras, y por eso no se podía registrar un documento extranjero.

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

