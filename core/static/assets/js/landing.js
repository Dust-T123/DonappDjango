/* Donapp · comportamiento de la página pública
   Barra de navegación · aparición al scroll · inclinación y brillo con el cursor
   · cifras y gráficos en vivo (/api/estadisticas) · galería y visor (/api/eventos) */
(function () {
  'use strict';

  var root = document.documentElement;
  var reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var canHover = window.matchMedia('(hover: hover) and (pointer: fine)').matches;
  var $ = function (sel, ctx) { return (ctx || document).querySelector(sel); };
  var $$ = function (sel, ctx) { return Array.prototype.slice.call((ctx || document).querySelectorAll(sel)); };
  var css = function (name) { return getComputedStyle(root).getPropertyValue(name).trim(); };
  root.classList.add('js');

  /* ── Barra de navegación ─────────────────────────────────────────── */
  function initNav() {
    var nav = $('#site-nav');
    if (!nav) return;
    var onScroll = function () { nav.classList.toggle('is-scrolled', window.scrollY > 60); };
    onScroll();
    window.addEventListener('scroll', onScroll, { passive: true });

    var links = $$('.site-nav-links a');
    var map = {};
    links.forEach(function (a) { var t = $(a.getAttribute('href')); if (t) map[t.id] = a; });
    if (!('IntersectionObserver' in window)) return;
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) {
        if (!e.isIntersecting || window.scrollY < 200) return;
        links.forEach(function (a) { a.removeAttribute('aria-current'); });
        map[e.target.id].setAttribute('aria-current', 'true');
      });
    }, { rootMargin: '-45% 0px -50% 0px' });
    Object.keys(map).forEach(function (id) { io.observe(document.getElementById(id)); });
  }

  /* ── Aparición al hacer scroll ───────────────────────────────────── */
  function initReveal() {
    var groups = $$('[data-reveal]');
    groups.forEach(function (g) { $$('.rise', g).forEach(function (el, i) { el.style.setProperty('--i', i); }); });
    if (!('IntersectionObserver' in window) || reduce) { groups.forEach(function (g) { g.classList.add('is-in'); }); return; }
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) { if (e.isIntersecting) { e.target.classList.add('is-in'); io.unobserve(e.target); } });
    }, { threshold: 0.12 });
    groups.forEach(function (g) { io.observe(g); });
  }

  /* ── Hero: foco de luz que sigue al cursor · inclinación de tarjetas ─ */
  function initPointerEffects() {
    if (reduce || !canHover) return;
    var hero = $('.hero-video-section');
    if (hero) {
      hero.addEventListener('pointermove', function (e) {
        var r = hero.getBoundingClientRect();
        hero.style.setProperty('--hx', (e.clientX - r.left) + 'px');
        hero.style.setProperty('--hy', (e.clientY - r.top) + 'px');
        hero.classList.add('is-hover');
      });
      hero.addEventListener('pointerleave', function () { hero.classList.remove('is-hover'); });
    }
    $$('.kpi-card, .feature-card').forEach(function (card) {
      var frame = 0;
      card.addEventListener('pointermove', function (e) {
        if (frame) return;
        frame = requestAnimationFrame(function () {
          frame = 0;
          var r = card.getBoundingClientRect(), x = (e.clientX - r.left) / r.width, y = (e.clientY - r.top) / r.height;
          card.style.setProperty('--ry', ((x - 0.5) * 8).toFixed(2) + 'deg');
          card.style.setProperty('--rx', ((0.5 - y) * 8).toFixed(2) + 'deg');
          card.style.setProperty('--mx', (e.clientX - r.left) + 'px');
          card.style.setProperty('--my', (e.clientY - r.top) + 'px');
        });
      });
      card.addEventListener('pointerleave', function () { card.style.setProperty('--rx', '0deg'); card.style.setProperty('--ry', '0deg'); });
      if (card.classList.contains('feature-card')) card.classList.add('glow');
    });
  }

  /* ── Impacto en vivo ─────────────────────────────────────────────── */
  var charts = { donut: null, bars: null };
  var totals = { donaciones: 0 };
  var fmt = new Intl.NumberFormat('es-CO');

  function countTo(el, to) {
    var from = parseInt(el.dataset.value || '0', 10);
    el.dataset.value = to;
    if (reduce || from === to) { el.textContent = fmt.format(to); return; }
    var t0 = null;
    (function tick(ts) {
      if (t0 === null) t0 = ts;
      var p = Math.min((ts - t0) / 1100, 1), eased = 1 - Math.pow(1 - p, 4);
      el.textContent = fmt.format(Math.round(from + (to - from) * eased));
      if (p < 1) requestAnimationFrame(tick);
    })(performance.now());
  }

  var centerPlugin = {
    id: 'donappCenter',
    afterDraw: function (chart) {
      var arc = chart.getDatasetMeta(0).data[0];
      if (!arc) return;
      var ctx = chart.ctx, r = arc.innerRadius;
      ctx.save();
      ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
      ctx.fillStyle = css('--text');
      ctx.font = '800 ' + Math.max(22, Math.round(r * 0.5)) + 'px ' + css('--ds-font-display');
      ctx.fillText(fmt.format(totals.donaciones), arc.x, arc.y - r * 0.08);
      ctx.fillStyle = css('--text-muted');
      ctx.font = '500 ' + Math.max(11, Math.round(r * 0.17)) + 'px ' + css('--ds-font');
      ctx.fillText('donaciones', arc.x, arc.y + r * 0.34);
      ctx.restore();
    }
  };

  function alpha(hex, a) {
    hex = hex.replace('#', '');
    if (hex.length === 3) hex = hex.split('').map(function (c) { return c + c; }).join('');
    var n = parseInt(hex, 16);
    return 'rgba(' + (n >> 16) + ',' + ((n >> 8) & 255) + ',' + (n & 255) + ',' + a + ')';
  }
  function palette() {
    return { blue: css('--ds-blue'), deep: css('--ds-blue-deep'), amber: '#F2A516', mute: alpha(css('--ds-slate'), 0.4), text: css('--text'), sub: css('--text-muted'), grid: css('--border') };
  }

  function buildCharts() {
    if (!window.Chart || charts.donut) return;
    var dCanvas = $('#chart-donaciones'), bCanvas = $('#chart-solicitudes');
    if (!dCanvas || !bCanvas) return;
    var animation = { duration: reduce ? 0 : 1000, easing: 'easeOutQuart' };

    charts.donut = new Chart(dCanvas, {
      type: 'doughnut',
      data: { labels: ['Aprobadas', 'Pendientes', 'Otros estados'], datasets: [{ data: [0, 0, 0], borderWidth: 0, hoverOffset: 12, spacing: 3, borderRadius: 8 }] },
      options: {
        responsive: true, maintainAspectRatio: false, cutout: '72%', animation: animation,
        plugins: {
          legend: { position: 'bottom', labels: { usePointStyle: true, pointStyle: 'circle', padding: 16, font: { family: css('--ds-font'), size: 12 } } },
          tooltip: { padding: 10, cornerRadius: 10, callbacks: { label: function (c) { var t = c.dataset.data.reduce(function (a, b) { return a + b; }, 0); return ' ' + c.label + ': ' + fmt.format(c.parsed) + (t ? ' (' + Math.round(c.parsed / t * 100) + '%)' : ''); } } }
        }
      },
      plugins: [centerPlugin]
    });

    charts.bars = new Chart(bCanvas, {
      type: 'bar',
      data: { labels: ['Donaciones', 'Solicitudes'], datasets: [{ label: 'Total', data: [0, 0], borderRadius: 10, borderSkipped: false, maxBarThickness: 54 }, { label: 'Aprobadas', data: [0, 0], borderRadius: 10, borderSkipped: false, maxBarThickness: 54 }] },
      options: {
        responsive: true, maintainAspectRatio: false, animation: animation, interaction: { mode: 'index', intersect: false },
        plugins: { legend: { position: 'bottom', labels: { usePointStyle: true, pointStyle: 'circle', padding: 16, font: { family: css('--ds-font'), size: 12 } } }, tooltip: { padding: 10, cornerRadius: 10 } },
        scales: { x: { grid: { display: false } }, y: { beginAtZero: true, ticks: { precision: 0 } } }
      }
    });
    paintCharts();
  }

  function paintCharts() {
    if (!charts.donut) return;
    var p = palette();
    var d = charts.donut;
    d.data.datasets[0].backgroundColor = [p.blue, p.amber, p.mute];
    d.options.plugins.legend.labels.color = p.sub;
    d.options.plugins.tooltip.backgroundColor = css('--ds-midnight') || '#070D24';
    d.update('none');
    var b = charts.bars;
    b.data.datasets[0].backgroundColor = p.mute;
    b.data.datasets[0].hoverBackgroundColor = p.sub;
    b.data.datasets[1].backgroundColor = p.blue;
    b.data.datasets[1].hoverBackgroundColor = p.deep;
    b.options.scales.x.ticks = { color: p.sub, font: { family: css('--ds-font'), size: 12 } };
    b.options.scales.y.ticks.color = p.sub;
    b.options.scales.y.grid = { color: p.grid };
    b.options.plugins.legend.labels.color = p.sub;
    b.options.plugins.tooltip.backgroundColor = css('--ds-midnight') || '#070D24';
    b.update('none');
  }

  function applyStats(data, generated) {
    var map = { total_donaciones: data.total_donaciones, total_solicitudes: data.total_solicitudes, total_donantes: data.total_donantes, eventos_activos: data.eventos_activos };
    $$('[data-kpi]').forEach(function (el) { countTo(el, map[el.dataset.kpi] || 0); });

    function ratio(total, ok) { return total ? Math.round(ok / total * 100) : 0; }
    var pd = ratio(data.total_donaciones, data.donaciones_aprobadas), ps = ratio(data.total_solicitudes, data.solicitudes_aprobadas);
    var set = function (id, v) { var el = document.getElementById(id); if (el) el.textContent = v; };
    var bar = function (id, v) { var el = document.getElementById(id); if (el) el.style.setProperty('--p', v); };
    bar('meter-donaciones', pd); bar('meter-solicitudes', ps);
    set('foot-donaciones', fmt.format(data.donaciones_aprobadas) + ' aprobadas · ' + pd + '%');
    set('foot-solicitudes', fmt.format(data.solicitudes_aprobadas) + ' aprobadas · ' + ps + '%');

    totals.donaciones = data.total_donaciones;
    if (charts.donut) {
      var otros = Math.max(0, data.total_donaciones - data.donaciones_aprobadas - data.donaciones_pendientes);
      charts.donut.data.datasets[0].data = [data.donaciones_aprobadas, data.donaciones_pendientes, otros];
      charts.donut.update();
      charts.bars.data.datasets[0].data = [data.total_donaciones, data.total_solicitudes];
      charts.bars.data.datasets[1].data = [data.donaciones_aprobadas, data.solicitudes_aprobadas];
      charts.bars.update();
    }
    var status = $('#impact-status');
    if (status) status.textContent = 'Datos actualizados el ' + generated + ' · se refrescan cada 30 segundos.';
  }

  function loadStats() {
    return fetch('/api/estadisticas', { headers: { Accept: 'application/json' } })
      .then(function (r) { return r.json(); })
      .then(function (json) { if (json && json.success) applyStats(json.data, json.generado); })
      .catch(function () {
        var status = $('#impact-status');
        if (status) status.textContent = 'No pudimos cargar las cifras ahora mismo. Lo intentaremos de nuevo en unos segundos.';
      });
  }

  function initImpact() {
    var section = $('#impacto');
    if (!section) return;
    var started = false, timer = null;
    function start() {
      if (started) return;
      started = true;
      buildCharts();
      loadStats();
      timer = setInterval(function () { if (document.visibilityState === 'visible') loadStats(); }, 30000);
    }
    if ('IntersectionObserver' in window) {
      var io = new IntersectionObserver(function (entries) { if (entries[0].isIntersecting) { start(); io.disconnect(); } }, { rootMargin: '200px' });
      io.observe(section);
    } else { start(); }
    document.addEventListener('donapp:themechange', paintCharts);
  }

  /* ── Galería + visor ─────────────────────────────────────────────── */
  function initGallery() {
    var grid = $('#gal-grid');
    if (!grid) return;
    var dlg = $('#lightbox');
    var items = [], index = 0, lastTrigger = null;

    function show(i) {
      index = (i + items.length) % items.length;
      var it = items[index];
      $('#lb-img').src = it.src;
      $('#lb-img').alt = it.title;
      $('#lb-title').textContent = it.title;
      $('#lb-meta').textContent = it.date;
      $('#lb-count').textContent = (index + 1) + ' de ' + items.length;
      var many = items.length > 1;
      $('#lb-prev').hidden = $('#lb-next').hidden = !many;
    }
    function open(i, trigger) {
      lastTrigger = trigger; show(i);
      if (typeof dlg.showModal === 'function') dlg.showModal(); else dlg.setAttribute('open', '');
    }
    function emptyState() {
      grid.className = '';
      grid.innerHTML = '';
      var box = document.createElement('div');
      box.className = 'gal-empty';
      box.innerHTML = '<i class="fa-regular fa-images" aria-hidden="true"></i><strong>Pronto compartiremos fotos de nuestros eventos</strong>Las imágenes que la fundación publique en cada evento aparecerán aquí.';
      grid.appendChild(box);
    }

    fetch('/api/eventos', { headers: { Accept: 'application/json' } })
      .then(function (r) { return r.json(); })
      .then(function (json) {
        var data = (json && json.success && json.data) || [];
        items = data.filter(function (ev) { return ev.publicacion && ev.publicacion.imagen; }).map(function (ev) {
          var pub = ev.publicacion, prog = ev.programacion || {};
          return { src: pub.imagen, title: pub.titulo || ev.nombre, date: (prog.lugar || '') + (prog.fecha_inicio ? ' · ' + String(prog.fecha_inicio).substring(0, 10).split('-').reverse().join('/') : '') };
        });
        if (!items.length) { emptyState(); return; }
        grid.className = 'gal-grid';
        grid.innerHTML = '';
        items.forEach(function (it, i) {
          var b = document.createElement('button');
          b.type = 'button'; b.className = 'gal-item rise';
          b.setAttribute('aria-label', 'Ampliar imagen: ' + it.title);
          var img = document.createElement('img');
          img.src = it.src; img.alt = ''; img.loading = 'lazy';
          var cap = document.createElement('span'); cap.className = 'gal-cap';
          var s = document.createElement('strong'); s.textContent = it.title;
          var m = document.createElement('small'); m.textContent = it.date;
          cap.appendChild(s); cap.appendChild(m); b.appendChild(img); b.appendChild(cap);
          b.style.setProperty('--i', i);
          b.addEventListener('click', function () { open(i, b); });
          grid.appendChild(b);
        });
        grid.classList.add('is-in');
      })
      .catch(emptyState);

    $('#lb-close').addEventListener('click', function () { dlg.close(); });
    $('#lb-prev').addEventListener('click', function () { show(index - 1); });
    $('#lb-next').addEventListener('click', function () { show(index + 1); });
    dlg.addEventListener('click', function (e) { if (e.target === dlg) dlg.close(); });
    dlg.addEventListener('keydown', function (e) {
      if (e.key === 'ArrowLeft') { e.preventDefault(); show(index - 1); }
      if (e.key === 'ArrowRight') { e.preventDefault(); show(index + 1); }
    });
    dlg.addEventListener('close', function () { if (lastTrigger) lastTrigger.focus(); });
  }

  function init() { initNav(); initReveal(); initPointerEffects(); initImpact(); initGallery(); }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init); else init();
})();
