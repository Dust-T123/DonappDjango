/* Validaciones compartidas por el registro y los tres paneles (donante, asistente, administrador).
 *
 * Reglas únicas para que los mismos campos se comporten igual en todos lados y coincidan
 * con las del servidor (core/forms.py):
 *   - numDocumento : según el tipo de documento. CC, TI, CE, TE y PPT: solo dígitos; Pasaporte:
 *                    letras y números (en mayúsculas). Siempre de 4 a 15 caracteres.
 *   - nombre/apellido : solo letras y espacios.
 *   - telefono     : solo dígitos, exactamente 10.
 *   - valorNuevo   : en las solicitudes de corrección cambia según el campo elegido.
 *   - celdas largas: se recortan con "…" y muestran el texto completo al pasar el cursor.
 */
(function () {
    'use strict';

    var LETRAS_FUERA = /[^A-Za-záéíóúÁÉÍÓÚüÜñÑ\s]/g;

    var TIPOS_CON_LETRAS = ['Pasaporte'];

    function admiteLetras(tipo)  { return TIPOS_CON_LETRAS.indexOf(tipo) !== -1; }
    function sanearDocumento(v)  { return v.replace(/[^A-Za-z0-9]/g, '').toUpperCase().slice(0, 15); }
    function sanearDigitos(v)    { return v.replace(/\D/g, '').slice(0, 15); }
    function sanearLetras(v)    { return v.replace(LETRAS_FUERA, '').replace(/^\s+/, '').replace(/\s{2,}/g, ' '); }
    function sanearTelefono(v)  { return v.replace(/\D/g, '').slice(0, 10); }

    function enVivo(input, saneador) {
        input.addEventListener('input', function () {
            var limpio = saneador(this.value);
            if (this.value !== limpio) this.value = limpio;
        });
    }

    function activo(input) { return !input.disabled && !input.readOnly; }

    // ── Documento, nombre, apellido y teléfono ────────────────────────────────
    function inicializarCampos() {
        document.querySelectorAll('input[name="numDocumento"]').forEach(function (inp) {
            if (!activo(inp)) return;
            var select = inp.form ? inp.form.querySelector('select[name="tipoDocumento"]') : null;
            inp.setAttribute('maxlength', '15');
            inp.setAttribute('minlength', '4');
            // Regla vigente según el tipo elegido (sin tipo todavía: solo dígitos, lo más común).
            function aplicar() {
                var letras = select ? admiteLetras(select.value) : true;
                if (letras) {
                    inp.setAttribute('pattern', '[A-Za-z0-9]{4,15}');
                    inp.setAttribute('inputmode', 'text');
                    inp.setAttribute('autocapitalize', 'characters');
                    inp.setAttribute('title', 'Entre 4 y 15 caracteres: solo letras y números');
                    inp.placeholder = 'Letras y números, 4 a 15 caracteres';
                } else {
                    inp.setAttribute('pattern', '[0-9]{4,15}');
                    inp.setAttribute('inputmode', 'numeric');
                    inp.removeAttribute('autocapitalize');
                    inp.setAttribute('title', 'Entre 4 y 15 dígitos: solo números');
                    inp.placeholder = 'Solo números, 4 a 15 dígitos';
                }
                var limpio = (letras ? sanearDocumento : sanearDigitos)(inp.value);
                if (inp.value !== limpio) inp.value = limpio;
            }
            aplicar();
            inp.addEventListener('input', function () {
                var l = (select && !admiteLetras(select.value) ? sanearDigitos : sanearDocumento)(this.value);
                if (this.value !== l) this.value = l;
            });
            if (select) select.addEventListener('change', aplicar);
        });
        document.querySelectorAll('input[name="nombre"], input[name="apellido"]').forEach(function (inp) {
            if (!activo(inp)) return;
            enVivo(inp, sanearLetras);
        });
        document.querySelectorAll('input[name="telefono"]').forEach(function (inp) {
            if (!activo(inp)) return;
            inp.setAttribute('maxlength', '10');
            enVivo(inp, sanearTelefono);
        });
    }

    // ── Límites únicos para los campos que comparten varios módulos ─────────────────
    // [mínimo, máximo] igual que en core/forms.py. Se aplican a cualquier formulario de la página,
    // así un campo no puede aceptar más (ni menos) caracteres en un módulo que en otro.
    var LIMITES = {
        nombre: [3, 100], apellido: [2, 100], direccion: [5, 255], email: [0, 150], necesidad: [0, 255],
        observacion_visita: [0, 500], password: [6, 30], password_confirmation: [0, 30],
        new_password1: [6, 30], new_password2: [0, 30], contrasena: [0, 30], nombre_categoria: [3, 100],
        justificacion: [10, 300], valorNuevo: [0, 150], texto: [3, 500]
    };
    function aplicarLimites() {
        document.querySelectorAll('input, textarea').forEach(function (el) {
            var l = LIMITES[el.name];
            if (!l || !activo(el)) return;
            if (el.name === 'nombre' && el.closest('form') && el.closest('form').querySelector('[name="nombre_categoria"]')) return;
            el.setAttribute('maxlength', String(l[1]));
            if (l[0] > 0) el.setAttribute('minlength', String(l[0]));
        });
    }

    // ── Campos solo numéricos: cantidad (1–9999) y código de verificación (6 dígitos) ─────
    function soloNumericos() {
        document.querySelectorAll('input[name="stock"]').forEach(function (inp) {
            if (!activo(inp)) return;
            inp.setAttribute('inputmode', 'numeric');
            inp.setAttribute('min', '1'); inp.setAttribute('max', '9999');
            inp.addEventListener('keydown', function (e) {
                if (['e', 'E', '+', '-', '.', ','].indexOf(e.key) !== -1) e.preventDefault();
            });
            inp.addEventListener('input', function () {
                var l = this.value.replace(/\D/g, '').slice(0, 4);
                if (this.value !== l) this.value = l;
            });
        });
        document.querySelectorAll('input[name="codigo"]').forEach(function (inp) {
            if (!activo(inp)) return;
            inp.setAttribute('maxlength', '6'); inp.setAttribute('inputmode', 'numeric'); inp.setAttribute('pattern', '[0-9]{6}');
            enVivo(inp, function (v) { return v.replace(/\D/g, '').slice(0, 6); });
        });
    }

    // ── Solicitudes de corrección: el campo "valor propuesto" depende del campo elegido ──
    var TIPOS = ['CC', 'TI', 'CE', 'TE', 'PPT', 'Pasaporte'];

    function haceAnios(n) {
        var d = new Date();
        var y = d.getFullYear() - n, m = d.getMonth(), dia = d.getDate();
        var f = new Date(y, m, dia);
        if (f.getMonth() !== m) f = new Date(y, m, 28);      // 29/02 -> 28/02
        return f.toISOString().split('T')[0];
    }

    function datalistTipos() {
        var dl = document.getElementById('lista_tipos_documento');
        if (dl) return dl;
        dl = document.createElement('datalist');
        dl.id = 'lista_tipos_documento';
        TIPOS.forEach(function (t) { var o = document.createElement('option'); o.value = t; dl.appendChild(o); });
        document.body.appendChild(dl);
        return dl;
    }

    function configurarValor(select, input) {
        var campo = select.value;
        var viejo = input._saneador;
        if (viejo) { input.removeEventListener('input', viejo); input._saneador = null; }
        ['pattern', 'minlength', 'list', 'min', 'max', 'title', 'autocapitalize'].forEach(function (a) { input.removeAttribute(a); });
        input.type = 'text';
        input.setAttribute('maxlength', '150');
        input.value = '';

        var saneador = null;
        if (campo === 'numDocumento') {
            input.setAttribute('maxlength', '15'); input.setAttribute('minlength', '4');
            input.setAttribute('pattern', '[A-Za-z0-9]{4,15}'); input.setAttribute('autocapitalize', 'characters');
            input.setAttribute('title', 'Entre 4 y 15 caracteres. Debe cumplir la regla del tipo de documento (solo dígitos; el pasaporte admite letras)');
            input.placeholder = 'Dígitos (pasaporte: letras y números)';
            saneador = sanearDocumento;
        } else if (campo === 'tipoDocumento') {
            datalistTipos();
            input.setAttribute('list', 'lista_tipos_documento');
            input.setAttribute('pattern', '(CC|TI|CE|TE|PPT|Pasaporte)');
            input.setAttribute('title', 'CC, TI, CE, TE, PPT o Pasaporte');
            input.placeholder = 'CC, TI, CE, TE, PPT o Pasaporte';
        } else if (campo === 'fechaNacimiento') {
            input.type = 'date';
            input.setAttribute('min', '1920-01-01');
            input.setAttribute('max', haceAnios(14));
        } else if (campo === 'nombre' || campo === 'apellido') {
            input.setAttribute('maxlength', '100');
            input.setAttribute('minlength', campo === 'nombre' ? '3' : '2');
            input.placeholder = 'Solo letras y espacios';
            saneador = sanearLetras;
        } else {
            input.placeholder = 'Escribe el valor correcto';
        }
        if (saneador) {
            input._saneador = function () { var l = saneador(this.value); if (this.value !== l) this.value = l; };
            input.addEventListener('input', input._saneador);
        }
    }

    function inicializarCorrecciones() {
        document.querySelectorAll('form').forEach(function (form) {
            var select = form.querySelector('select[name="campo"]');
            var input = form.querySelector('input[name="valorNuevo"]');
            if (!select || !input) return;
            select.addEventListener('change', function () { configurarValor(select, input); });
            form.addEventListener('reset', function () { setTimeout(function () { configurarValor(select, input); }, 0); });
        });
    }

    // ── Celdas con texto largo: recortar y mostrar el completo en el tooltip ──
    function marcarCeldasLargas() {
        document.querySelectorAll('.table-wrap td').forEach(function (td) {
            if (td.classList.contains('td-actions') || td.classList.contains('td-wrap') || td.querySelector('button, a, form, input, select, textarea')) return;
            var texto = (td.textContent || '').replace(/\s+/g, ' ').trim();
            var recortable = td.classList.contains('td-desc') || td.classList.contains('td-cat') ||
                             td.classList.contains('td-obs') || td.classList.contains('td-trunc');
            if (!recortable && texto.length > 28 && !td.querySelector('.badge')) {
                td.classList.add('td-trunc');
                recortable = true;
            }
            if (recortable && texto.length > 0 && !td.getAttribute('title')) td.setAttribute('title', texto);
        });
    }
    window.marcarCeldasLargas = marcarCeldasLargas;

    document.addEventListener('DOMContentLoaded', function () {
        inicializarCampos();
        aplicarLimites();
        soloNumericos();
        inicializarCorrecciones();
        marcarCeldasLargas();
    });
})();
