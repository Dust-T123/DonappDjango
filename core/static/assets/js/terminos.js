/**
 * terminos.js
 * Lógica interactiva de la página de Términos y Condiciones.
 * Sin código inline en el HTML.
 */

document.addEventListener('DOMContentLoaded', () => {

    // ─────────────────────────────────────────
    // ACORDEÓN
    // ─────────────────────────────────────────

    /**
     * Alterna un ítem del acordeón.
     * Se cierra el que estaba abierto antes de abrir el nuevo.
     * @param {HTMLButtonElement} btn - botón clickeado
     */
    function toggleAccordion(btn) {
        const body   = btn.nextElementSibling;
        const isOpen = body.classList.contains('open');
        const parent = btn.closest('.tc-accordion');

        // Cierra todos los ítems del mismo acordeón
        parent.querySelectorAll('.accordion-body').forEach(b => b.classList.remove('open'));
        parent.querySelectorAll('.accordion-btn').forEach(b => b.classList.remove('open'));

        // Abre el clickeado solo si estaba cerrado
        if (!isOpen) {
            body.classList.add('open');
            btn.classList.add('open');
        }
    }

    // Delegar el click en todos los botones del acordeón
    document.querySelectorAll('.accordion-btn').forEach(btn => {
        btn.addEventListener('click', () => toggleAccordion(btn));
    });


    // ─────────────────────────────────────────
    // BARRA DE ACEPTACIÓN FIJA
    // FIX SCROLL: pointer-events:none cuando está oculta,
    // padding-bottom en body cuando está visible.
    // ─────────────────────────────────────────

    const acceptBar = document.getElementById('acceptBar');
    const acceptBtn = document.getElementById('acceptBtn');
    let   barShown  = false;

    // La barra fija mide distinto en móvil: el botón de preferencias se coloca justo encima de ella.
    function medirBarra() {
        document.documentElement.style.setProperty('--accept-bar-h', acceptBar.offsetHeight + 'px');
    }
    window.addEventListener('resize', medirBarra);

    function showAcceptBar() {
        if (barShown) return;
        acceptBar.classList.add('visible');
        document.body.classList.add('accept-bar-open');  // reserva espacio inferior
        medirBarra();
        barShown = true;
    }

    window.addEventListener('scroll', () => {
        const scrolled = window.scrollY / (document.body.scrollHeight - window.innerHeight);
        if (scrolled > 0.15) showAcceptBar();
    }, { passive: true });   // passive:true mejora rendimiento del scroll en móvil

    function acceptTerms() {
        acceptBtn.disabled = true;
        acceptBtn.innerHTML = '<i class="fa-solid fa-circle-check"></i>&nbsp; ¡Aceptado!';
        acceptBtn.classList.add('confirmed');

        // Se recuerda la aceptación: el formulario de registro marca la casilla solo (también en otra pestaña).
        try { localStorage.setItem('donapp:terminos', String(Date.now())); } catch (e) { /* sin almacenamiento */ }

        // Destino según el estado: con sesión iniciada → su panel; sin sesión → registro
        // (o inicio de sesión si venía de allí).
        const d = acceptBar.dataset;
        let destino, mensaje;
        if (d.autenticado === '1' && d.panel) {
            destino = d.panel; mensaje = 'Gracias por aceptar. Te llevamos a tu panel…';
        } else if (document.referrer && /\/login\/?(\?|$)/.test(new URL(document.referrer, location.href).pathname)) {
            destino = d.login; mensaje = 'Gracias por aceptar. Te llevamos al inicio de sesión…';
        } else {
            destino = d.registro; mensaje = 'Gracias por aceptar. Te llevamos al registro…';
        }
        const msg = document.getElementById('acceptMsg');
        if (msg) msg.textContent = mensaje;
        setTimeout(() => { window.location.assign(destino); }, 1200);
    }

    if (acceptBtn) {
        acceptBtn.addEventListener('click', acceptTerms);
    }


    // ─────────────────────────────────────────
    // ÍNDICE ACTIVO AL HACER SCROLL
    // ─────────────────────────────────────────

    const sections  = document.querySelectorAll('.tc-section');
    const navLinks  = document.querySelectorAll('.tc-index-bar a');

    // Referencia al contenedor scrollable del índice (scroll horizontal)
    const indexBar = document.querySelector('.tc-index-bar');

    const sectionObserver = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (!entry.isIntersecting) return;

            navLinks.forEach(link => link.classList.remove('active'));

            const activeLink = document.querySelector(
                `.tc-index-bar a[href="#${entry.target.id}"]`
            );

            if (activeLink && indexBar) {
                activeLink.classList.add('active');

                // Desplaza SOLO el contenedor del índice en horizontal,
                // sin afectar el scroll vertical de la página.
                const barRect  = indexBar.getBoundingClientRect();
                const linkRect = activeLink.getBoundingClientRect();
                const offset   = linkRect.left - barRect.left
                               - (barRect.width / 2)
                               + (linkRect.width / 2);

                indexBar.scrollBy({ left: offset, behavior: 'smooth' });
            }
        });
    }, {
        rootMargin: '-30% 0px -60% 0px'
    });

    sections.forEach(section => sectionObserver.observe(section));


    // ─────────────────────────────────────────
    // LOGO FALLBACK (reemplaza onerror inline)
    // ─────────────────────────────────────────

    const headerLogo    = document.getElementById('headerLogo');
    const headerFallback = document.getElementById('headerFallback');

    if (headerLogo) {
        headerLogo.addEventListener('error', () => {
            headerLogo.style.display    = 'none';
            if (headerFallback) headerFallback.style.display = 'block';
        });
    }

    const footerLogo = document.getElementById('footerLogo');
    if (footerLogo) {
        footerLogo.addEventListener('error', () => {
            footerLogo.style.display = 'none';
        });
    }

});