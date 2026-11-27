/* Detalles de solo lectura para el administrador y el asistente.
 * Las tablas recortan el texto largo; aquí se ve completo (artículos del stock, donaciones y
 * solicitudes —también las canceladas, que no se pueden modificar— y visitas domiciliarias). */
(function () {
    'use strict';

    function esc(v) {
        return String(v == null ? '' : v).replace(/[&<>"']/g, function (c) {
            return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
        });
    }
    function fila(etiqueta, valor) {
        var vacio = valor === null || valor === undefined || valor === '';
        return '<div class="detalle-fila"><dt>' + esc(etiqueta) + '</dt><dd>' + (vacio ? '<span class="text-muted">—</span>' : esc(valor)) + '</dd></div>';
    }
    function lista(filas) { return '<dl class="detalle-lista">' + filas.map(function (f) { return fila(f[0], f[1]); }).join('') + '</dl>'; }

    function abrir(titulo, icono, filas, nota) {
        document.getElementById('dg_titulo').innerHTML = '<i class="fa-solid ' + icono + '" aria-hidden="true"></i> ' + esc(titulo);
        document.getElementById('dg_cuerpo').innerHTML = lista(filas);
        var n = document.getElementById('dg_nota');
        n.hidden = !nota;
        n.innerHTML = nota ? '<i class="fa-solid fa-lock" aria-hidden="true"></i> ' + esc(nota) : '';
        var m = document.getElementById('modalDetalleGeneral');
        m.style.display = 'flex';
        var cerrar = m.querySelector('.modal-close');
        if (cerrar) cerrar.focus();
    }
    var CANCELADA = 'Esta ficha está cancelada: queda como constancia en el historial y solo puede consultarse.';

    window.detalleStock = function (i) {
        abrir('Artículo en stock', 'fa-boxes-stacked', [
            ['Artículo', i.articulo], ['Categoría', i.categoria],
            ['Cantidad disponible', i.cantidad + (i.cantidad === 1 ? ' unidad' : ' unidades')], ['Donaciones que lo componen', i.donaciones]]);
    };
    window.detalleDonacion = function (d) {
        abrir('Donación #' + d.idDonacion, 'fa-box-open', [
            ['Descripción', d.descripcion], ['Categoría', d.categoria], ['Cantidad (stock)', d.stock],
            ['Estado', d.estado], ['Donante', d.donante], ['Fecha de registro', d.fechaCreacion ? String(d.fechaCreacion).slice(0, 10).split('-').reverse().join('/') : null],
            ['Observación', d.observacion]], d.estado === 'cancelada' ? CANCELADA : '');
    };
    window.detalleSolicitud = function (s) {
        abrir('Solicitud #' + s.idSolicitud, 'fa-clipboard-list', [
            ['Descripción', s.descripcion], ['Categoría', s.categoria], ['Estado', s.estado],
            ['Solicitante', s.solicitante], ['Prioridad del beneficiario', s.prioridad], ['Gestor', s.nombre_gestor],
            ['Fecha de solicitud', s.fechaCreacion ? String(s.fechaCreacion).slice(0, 10).split('-').reverse().join('/') : null],
            ['Observación', s.observacion]], s.estado === 'cancelada' ? CANCELADA : '');
    };
    // HTML del recuadro de información de la visita (lo usa el modal «Gestionar visita»).
    window.detalleVisitaHtml = function (v) {
        return lista([
            ['Beneficiario', v.usuario], ['Estado', v.estado], ['Dirección', v.direccion], ['Motivo', v.motivo],
            ['Fecha preferida', v.fechaPreferida], ['Solicitada', v.fechaSolicitud],
            ['Resuelta', v.fechaResolucion], ['Gestor', v.gestor], ['Observación', v.observacion]]);
    };

    document.addEventListener('keydown', function (e) {
        var m = document.getElementById('modalDetalleGeneral');
        if (e.key === 'Escape' && m && m.style.display === 'flex') m.style.display = 'none';
    });
})();
