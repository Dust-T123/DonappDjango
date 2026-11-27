/* Donapp Design System · comportamiento compartido
   Módulos: preferencias (tema y accesibilidad) · menú móvil · tablas apiladas
            · brillo con el cursor · cifras animadas · gráfico de resumen · carga en formularios */
(function () {
  'use strict';

  var root = document.documentElement;
  var reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var $ = function (id) { return document.getElementById(id); };

  var store = {
    get: function (k) { try { return localStorage.getItem('donapp:' + k); } catch (e) { return null; } },
    set: function (k, v) { try { localStorage.setItem('donapp:' + k, v); } catch (e) { /* sin almacenamiento */ } },
    del: function (k) { try { localStorage.removeItem('donapp:' + k); } catch (e) { /* sin almacenamiento */ } }
  };
  var emit = function (name) { document.dispatchEvent(new CustomEvent(name)); };

  /* ── Preferencias ─────────────────────────────────────────────────── */
  var FS_STEPS = [0.875, 1, 1.125, 1.25, 1.375, 1.5];

  var prefs = {
    theme: function () { return root.getAttribute('data-theme') === 'dark' ? 'dark' : 'light'; },
    fs: function () { var v = parseFloat(store.get('fs')); return FS_STEPS.indexOf(v) > -1 ? v : 1; },
    boost: function () { var v = parseInt(store.get('boost'), 10); return isNaN(v) ? 0 : Math.min(100, Math.max(0, v)); },
    hc: function () { return store.get('hc') === '1'; }
  };

  function paintControls() {
    var themeBtn = $('ds-theme');
    if (themeBtn) {
      var dark = prefs.theme() === 'dark';
      themeBtn.setAttribute('aria-checked', String(dark));
      themeBtn.setAttribute('title', dark ? 'Cambiar a modo claro' : 'Cambiar a modo oscuro');
    }
    if ($('ds-fs-out')) $('ds-fs-out').textContent = Math.round(prefs.fs() * 100) + '%';
    if ($('ds-boost')) $('ds-boost').value = prefs.boost();
    if ($('ds-boost-out')) $('ds-boost-out').textContent = prefs.boost() + '%';
    if ($('ds-hc')) $('ds-hc').checked = prefs.hc();
    if ($('ds-fs-down')) $('ds-fs-down').disabled = prefs.fs() === FS_STEPS[0];
    if ($('ds-fs-up')) $('ds-fs-up').disabled = prefs.fs() === FS_STEPS[FS_STEPS.length - 1];
  }

  function setTheme(t) {
    root.setAttribute('data-theme', t);
    store.set('theme', t);
    paintControls();
    emit('donapp:themechange');
  }
  function setFontScale(v) {
    root.style.setProperty('--ds-fs', v);
    if (v === 1) store.del('fs'); else store.set('fs', v);
    paintControls();
  }
  function setBoost(v) {
    root.style.setProperty('--ds-boost', v);
    if (v === 0) store.del('boost'); else store.set('boost', v);
    paintControls();
    emit('donapp:themechange');
  }
  function setHighContrast(on) {
    if (on) { root.setAttribute('data-contrast', 'high'); store.set('hc', '1'); }
    else { root.removeAttribute('data-contrast'); store.del('hc'); }
    paintControls();
    emit('donapp:themechange');
  }

  function initPreferences() {
    var themeBtn = $('ds-theme');
    if (!themeBtn) return;
    themeBtn.addEventListener('click', function () { setTheme(prefs.theme() === 'dark' ? 'light' : 'dark'); });

    var btn = $('ds-a11y-btn'), panel = $('ds-a11y');
    function openPanel(open) {
      panel.hidden = !open;
      btn.setAttribute('aria-expanded', String(open));
      if (open) { var first = panel.querySelector('button, input'); if (first) first.focus(); }
    }
    btn.addEventListener('click', function () { openPanel(panel.hidden); });
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && !panel.hidden) { openPanel(false); btn.focus(); }
    });
    document.addEventListener('click', function (e) {
      if (!panel.hidden && !e.target.closest('.ds-dock')) openPanel(false);
    });

    $('ds-fs-down').addEventListener('click', function () {
      var i = FS_STEPS.indexOf(prefs.fs()); if (i > 0) setFontScale(FS_STEPS[i - 1]);
    });
    $('ds-fs-up').addEventListener('click', function () {
      var i = FS_STEPS.indexOf(prefs.fs()); if (i < FS_STEPS.length - 1) setFontScale(FS_STEPS[i + 1]);
    });
    $('ds-boost').addEventListener('input', function (e) { setBoost(parseInt(e.target.value, 10)); });
    $('ds-hc').addEventListener('change', function (e) { setHighContrast(e.target.checked); });
    $('ds-reset').addEventListener('click', function () {
      ['fs', 'boost', 'hc'].forEach(store.del);
      root.style.removeProperty('--ds-fs');
      root.style.removeProperty('--ds-boost');
      root.removeAttribute('data-contrast');
      setTheme(window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
      store.del('theme');
      paintControls();
    });
    paintControls();
  }

  /* ── Destino del enlace "Saltar al contenido" ─────────────────────── */
  function initSkipTarget() {
    var main = document.querySelector('main, .main-content, .caja-exterior, .recover-card, #landing-page');
    if (main && !main.id) main.id = 'ds-main';
    if (main) main.setAttribute('tabindex', '-1');
    var skip = document.querySelector('.ds-skip');
    if (skip && main) skip.setAttribute('href', '#' + main.id);
  }

  /* ── Menú lateral en móvil ────────────────────────────────────────── */
  function initMobileNav() {
    var sidebar = document.querySelector('.admin-wrapper .sidebar');
    if (!sidebar) return;
    sidebar.id = sidebar.id || 'ds-sidebar';
    var btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'ds-menu-btn';
    btn.setAttribute('aria-controls', sidebar.id);
    btn.setAttribute('aria-expanded', 'false');
    btn.setAttribute('aria-label', 'Abrir menú de navegación');
    btn.innerHTML = '<i class="fa-solid fa-bars" aria-hidden="true"></i>';
    document.body.appendChild(btn);

    function toggle(open) {
      document.body.classList.toggle('ds-nav-open', open);
      btn.setAttribute('aria-expanded', String(open));
      btn.setAttribute('aria-label', open ? 'Cerrar menú de navegación' : 'Abrir menú de navegación');
      btn.firstElementChild.className = open ? 'fa-solid fa-xmark' : 'fa-solid fa-bars';
    }
    btn.addEventListener('click', function () { toggle(!document.body.classList.contains('ds-nav-open')); });
    sidebar.addEventListener('click', function (e) { if (e.target.closest('a.nav-link')) toggle(false); });
    document.addEventListener('click', function (e) { if (e.target === document.body) toggle(false); });
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && document.body.classList.contains('ds-nav-open')) { toggle(false); btn.focus(); }
    });
    window.matchMedia('(min-width: 901px)').addEventListener('change', function () { toggle(false); });
  }

  /* ── Tablas como tarjetas en pantallas pequeñas ───────────────────── */
  function labelTables() {
    document.querySelectorAll('table').forEach(function (table) {
      var headRow = table.querySelector('thead tr:last-child');
      if (!headRow) return;
      var labels = Array.prototype.map.call(headRow.children, function (th) { return th.textContent.trim(); });
      table.querySelectorAll('tbody tr').forEach(function (tr) {
        var i = 0;
        Array.prototype.forEach.call(tr.children, function (td) {
          if (td.hasAttribute('colspan')) { i += parseInt(td.getAttribute('colspan'), 10) || 1; return; }
          if (labels[i] && !td.hasAttribute('data-label')) td.setAttribute('data-label', labels[i]);
          i += 1;
        });
      });
      table.classList.add('ds-stack');
      // La última columna con botones (acciones) queda fija a la derecha para no perderla al desplazar.
      var filas = table.querySelectorAll('tbody tr');
      var conAcciones = Array.prototype.some.call(filas, function (tr) {
        var ult = tr.lastElementChild; return ult && !ult.hasAttribute('colspan') && ult.querySelector('button, a.btn, form');
      });
      if (conAcciones && headRow.lastElementChild) {
        headRow.lastElementChild.classList.add('td-sticky');
        Array.prototype.forEach.call(filas, function (tr) { if (tr.lastElementChild && !tr.lastElementChild.hasAttribute('colspan')) tr.lastElementChild.classList.add('td-sticky'); });
      }
    });
  }
  function initTables() {
    labelTables();
    var queued = false;
    new MutationObserver(function () {
      if (queued) return;
      queued = true;
      requestAnimationFrame(function () { queued = false; labelTables(); });
    }).observe(document.body, { childList: true, subtree: true });
  }

  /* ── Brillo que sigue al cursor ───────────────────────────────────── */
  function initGlow() {
    if (reduceMotion || !window.matchMedia('(hover: hover)').matches) return;
    var frame = 0;
    document.addEventListener('pointermove', function (e) {
      var card = e.target.closest && e.target.closest('.stat-card, .reporte-card, .card.ds-glow');
      if (!card || frame) return;
      frame = requestAnimationFrame(function () {
        frame = 0;
        var r = card.getBoundingClientRect();
        card.style.setProperty('--mx', (e.clientX - r.left) + 'px');
        card.style.setProperty('--my', (e.clientY - r.top) + 'px');
      });
    }, { passive: true });
  }

  /* ── Cifras que cuentan hasta su valor ────────────────────────────── */
  function initCountUp() {
    if (reduceMotion) return;
    document.querySelectorAll('.stat-card h3').forEach(function (el) {
      var raw = el.textContent.trim();
      if (!/^\d{1,6}$/.test(raw)) return;
      var target = parseInt(raw, 10);
      if (target < 2) return;
      var start = null;
      el.setAttribute('aria-label', raw);
      (function tick(ts) {
        if (start === null) start = ts;
        var p = Math.min((ts - start) / 700, 1);
        el.textContent = Math.round(target * (1 - Math.pow(1 - p, 3)));
        if (p < 1) requestAnimationFrame(tick); else el.textContent = raw;
      })(performance.now());
    });
  }

  /* ── Gráfico de resumen con los datos que ya muestran las tarjetas ── */
  function initSummaryChart() {
    if (!window.Chart) return;
    var grid = document.querySelector('.stats-grid');
    if (!grid || grid.dataset.dsChart) return;
    var items = [];
    grid.querySelectorAll('.stat-card').forEach(function (card) {
      var h = card.querySelector('h3'), p = card.querySelector('p');
      var value = h ? parseInt(h.getAttribute('aria-label') || h.textContent, 10) : NaN;
      if (p && !isNaN(value)) items.push({ label: p.textContent.trim(), value: value });
    });
    if (items.length < 3) return;
    grid.dataset.dsChart = '1';

    var section = document.createElement('section');
    section.className = 'card ds-chart-card ds-glow';
    section.setAttribute('aria-labelledby', 'ds-chart-title');
    section.innerHTML =
      '<h2 id="ds-chart-title">Resumen de actividad</h2>' +
      '<p>Pasa el cursor sobre una barra para ver el valor exacto.</p>' +
      '<div class="ds-chart-box"><canvas role="img"></canvas></div>';
    grid.insertAdjacentElement('afterend', section);

    var canvas = section.querySelector('canvas');
    canvas.setAttribute('aria-label', 'Gráfico de barras: ' + items.map(function (i) { return i.label + ' ' + i.value; }).join(', '));
    var css = function (name) { return getComputedStyle(root).getPropertyValue(name).trim(); };

    var chart = new Chart(canvas, {
      type: 'bar',
      data: { labels: items.map(function (i) { return i.label; }), datasets: [{ data: items.map(function (i) { return i.value; }), borderRadius: 8, borderSkipped: false, maxBarThickness: 26 }] },
      options: {
        indexAxis: 'y', responsive: true, maintainAspectRatio: false,
        animation: { duration: reduceMotion ? 0 : 700 },
        plugins: { legend: { display: false }, tooltip: { padding: 10, cornerRadius: 10, displayColors: false } },
        scales: { x: { beginAtZero: true, ticks: { precision: 0 } }, y: { grid: { display: false } } }
      }
    });
    function paint() {
      var ds = chart.data.datasets[0], o = chart.options;
      ds.backgroundColor = css('--ds-blue'); ds.hoverBackgroundColor = css('--ds-blue-deep');
      o.scales.x.ticks.color = o.scales.y.ticks.color = css('--text-muted');
      o.scales.x.grid.color = css('--border');
      o.plugins.tooltip.backgroundColor = css('--ds-midnight') || '#070D24';
      o.plugins.tooltip.titleColor = o.plugins.tooltip.bodyColor = '#fff';
      chart.update('none');
    }
    paint();
    document.addEventListener('donapp:themechange', paint);
  }

  /* ── Estado de carga al enviar formularios válidos ────────────────── */
  function initSubmitFeedback() {
    document.addEventListener('submit', function (e) {
      if (e.defaultPrevented) return;
      var form = e.target;
      if (form.hasAttribute('data-no-loading') || form.target === '_blank') return;
      var btn = e.submitter || form.querySelector('[type="submit"]');
      if (!btn || btn.classList.contains('is-loading')) return;
      btn.classList.add('is-loading');
      btn.setAttribute('aria-busy', 'true');
      setTimeout(function () { btn.classList.remove('is-loading'); btn.removeAttribute('aria-busy'); }, 10000);
    });
    window.addEventListener('pageshow', function () {
      document.querySelectorAll('.is-loading').forEach(function (b) { b.classList.remove('is-loading'); b.removeAttribute('aria-busy'); });
    });
  }

  function init() {
    initPreferences();
    initSkipTarget();
    initMobileNav();
    initTables();
    initGlow();
    initCountUp();
    initSummaryChart();
    initSubmitFeedback();
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init); else init();
})();
