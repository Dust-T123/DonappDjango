/**
 * DONAPP - Sistema de Gestión de Donaciones
 * JS Principal optimizado para integración con PHP
 */

document.addEventListener('DOMContentLoaded', () => {
    console.log('✅ DONAPP cargado correctamente');
    initHeroParticles();
    actualizarEstadisticas();
    statsInterval = setInterval(actualizarEstadisticas, 30000);
    cargarEventosAPI();
    setInterval(() => {
        cargarEventosAPI().then(() => {
            // Si el modal de detalle está abierto, refresca su contenido con los
            // datos frescos del mismo evento (por id, no por una clase CSS que
            // se pierde al reconstruir la cuadrícula cada vez).
            const modal = document.getElementById('modal-detalle-publicacion');
            if (modal && modal.classList.contains('active') && window.eventoAbiertoId) {
                const cardActualizada = document.querySelector(`.api-evento-card[data-evento-id="${window.eventoAbiertoId}"]`);
                if (cardActualizada) {
                    verDetallePublicacion(JSON.parse(cardActualizada.dataset.ev));
                }
            }
        });
    }, 30000);
});
// ========== MODALES ==========

function showModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.add('active');
        document.body.style.overflow = 'hidden'; // Evita scroll de fondo
    }
}

function closeModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.remove('active');
        document.body.style.overflow = 'auto';
        if (modalId === 'modal-detalle-publicacion') {
            window.eventoAbiertoId = null;
        }
    }
}

// Cerrar modales al hacer clic fuera del contenido
window.addEventListener('click', (event) => {
    if (event.target.classList.contains('modal')) {
        event.target.classList.remove('active');
        document.body.style.overflow = 'auto';
        if (event.target.id === 'modal-detalle-publicacion') {
            window.eventoAbiertoId = null;
        }
    }
});

// ========== VER DETALLE DE PUBLICACIÓN ==========

function verDetallePublicacion(data) {
    // 1. Normalizar estado
    const estadoLimpio = data.estado.trim().toLowerCase();
    const textoEstado = estadoLimpio === 'activo' ? 'Activo' : 'Finalizado';
    const claseEstado = estadoLimpio === 'activo' ? 'badge-activo' : 'badge-inactivo';

    // 2. Llenar elementos de texto básicos
    document.getElementById('detalle-titulo').textContent = data.titulo;
    document.getElementById('detalle-contenido').textContent = data.contenido;
    document.getElementById('detalle-evento').innerHTML = `<i class="fa-solid fa-tag"></i> ${data.evento}`;
    document.getElementById('detalle-entrega').textContent = data.entrega;
    document.getElementById('detalle-lugar').textContent = data.lugar;
    document.getElementById('detalle-autor').innerHTML = data.autor
        ? `<i class="fa-regular fa-user"></i> Publicado por ${data.autor}`
        : '';

    // 3. Construir el Header (Estado y Fecha) con margen superior
    const detalleHeader = document.getElementById('detalle-header');
    let htmlHeader = `
        <div style="display:flex; justify-content:space-between; align-items:center; margin-top: 10px; margin-bottom: 20px; width: 100%; padding-right: 50px;">
            <span class="publicacion-badge ${claseEstado}">${textoEstado}</span>
            <span class="publicacion-fecha" style="color: var(--color-text-muted); font-size: 0.9rem; font-weight: 500;">
                <i class="fa-regular fa-calendar"></i> ${data.fecha}
            </span>
        </div>`;

    detalleHeader.innerHTML = htmlHeader;

    // 4. Gestión de la Imagen (TIPO PÓSTER - SIN CORTAR)
    const imgPrevia = document.getElementById('detalle-imagen-bloque');
    if (imgPrevia) imgPrevia.remove();

    if (data.imagen && data.imagen.trim() !== '') {
        const infoBox = document.querySelector('.detalle-info-box');
        const pImagenBloque = document.createElement('div');
        pImagenBloque.id = 'detalle-imagen-bloque';

        // Contenedor con fondo neutro por si la imagen es muy delgada
        pImagenBloque.style.cssText = `
            margin-top: 15px; 
            margin-bottom: 25px; 
            width: 100%; 
            background: #f8f9fa; 
            border-radius: 12px; 
            overflow: hidden;
            display: flex;
            justify-content: center;
        `;

        const pImagen = document.createElement('img');
        pImagen.src = data.imagen;

        /* CAMBIO CLAVE: 
           - max-height: 500px (ajusta este valor según prefieras el alto máximo)
           - object-fit: contain (Muestra la imagen completa sin recortes)
        */
        pImagen.style.cssText = `
            width: 100%; 
            max-height: 500px; 
            object-fit: contain; 
            display: block;
            background: #f8f9fa;
        `;

        pImagenBloque.appendChild(pImagen);

        if (infoBox) {
            infoBox.parentNode.insertBefore(pImagenBloque, infoBox);
        }
    }

    // 5. Ajustes de estructura del Modal
    const modalContent = document.querySelector('.detalle-publicacion-content');
    if (modalContent) {
        modalContent.style.display = 'block';
        modalContent.style.position = 'relative';
        modalContent.style.padding = '20px 25px';
    }

    // 6. Botón Cerrar (X) - Estilizado y sobre la imagen si es necesario
    const closeBtn = document.querySelector('#modal-detalle-publicacion .modal-close');
    if (closeBtn) {
        closeBtn.style.cssText = `
            position: absolute !important;
            top: 15px !important;
            right: 15px !important;
            background: white;
            color: #333;
            border-radius: 50%;
            width: 35px;
            height: 35px;
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 1000;
            box-shadow: 0 2px 10px rgba(0,0,0,0.2);
            border: 1px solid #eee;
            cursor: pointer;
        `;
    }

    showModal('modal-detalle-publicacion');
}

// ========== UTILIDADES VISUALES ==========

function initHeroParticles() {
    const container = document.getElementById('particles-container');
    if (!container) return;

    const count = 30;
    for (let i = 0; i < count; i++) {
        const p = document.createElement('div');
        p.className = 'particle';
        p.style.cssText = `
            position: absolute;
            background: rgba(255,255,255,0.2);
            border-radius: 50%;
            left: ${Math.random() * 100}%;
            top: ${Math.random() * 100}%;
            width: ${2 + Math.random() * 6}px;
            height: ${2 + Math.random() * 6}px;
            animation: float ${6 + Math.random() * 10}s linear infinite;
            animation-delay: ${Math.random() * 5}s;
            pointer-events: none;
        `;
        container.appendChild(p);
    }
}

// Estilo para la animación de las partículas (inyectado)
const style = document.createElement('style');
style.innerHTML = `
    @keyframes float {
        0% { transform: translateY(0) translateX(0); opacity: 0; }
        50% { opacity: 0.5; }
        100% { transform: translateY(-100vh) translateX(20px); opacity: 0; }
    }
`;
document.head.appendChild(style);
// ========== API: ESTADÍSTICAS EN TIEMPO REAL ==========
const API_BASE = '/api';
let statsInterval = null;

function animarContador(elemento, valorFinal) {
    if (!elemento) return;
    const duracion = 1200;
    const inicio = parseInt(elemento.textContent.replace(/\D/g, '')) || 0;
    const diferencia = valorFinal - inicio;
    const pasos = 40;
    let paso = 0;

    const timer = setInterval(() => {
        paso++;
        const progreso = paso / pasos;
        const ease = 1 - Math.pow(1 - progreso, 3); // ease-out cúbico
        const actual = Math.round(inicio + diferencia * ease);
        elemento.textContent = '+' + actual;
        if (paso >= pasos) {
            clearInterval(timer);
            elemento.textContent = '+' + valorFinal;
        }
    }, duracion / pasos);
}

async function actualizarEstadisticas() {
    try {
        const res = await fetch(`${API_BASE}/estadisticas`);
        const json = await res.json();
        if (!json.success) return;

        const d = json.data;

        const statEls = document.querySelectorAll('.hero-stat');
        statEls.forEach(el => {
            // Leer el span de texto dentro del div, no el icono emoji
            const divEl = el.querySelector('div');
            const strong = divEl ? divEl.querySelector('strong') : null;
            const spanEl = divEl ? divEl.querySelector('span') : null;
            const label = spanEl ? spanEl.textContent.trim().toLowerCase() : '';
            if (!strong) return;

            if (label.includes('donacion'))
                animarContador(strong, d.total_donaciones);
            else if (label.includes('usuario'))
                animarContador(strong, d.total_donantes);
            else if (label.includes('evento'))
                animarContador(strong, d.eventos_activos);
        });

        const indicador = document.getElementById('stats-live-indicator');
        if (indicador) {
            indicador.classList.add('pulso');
            setTimeout(() => indicador.classList.remove('pulso'), 1000);
            indicador.title = `Última actualización: ${json.generado}`;
        }
    } catch (e) {
        console.warn('No se pudieron actualizar las estadísticas:', e);
    }
}

// ========== API: EVENTOS EN VIVO ==========

function formatearFechaEvento(fechaStr) {
    if (!fechaStr) return 'Pendiente';
    const partes = String(fechaStr).substring(0, 10).split('-');
    if (partes.length === 3) return `${partes[2]}/${partes[1]}/${partes[0]}`;
    return fechaStr;
}

function formatearRangoFechasEvento(inicio, fin) {
    if (!inicio && !fin) return 'Pendiente';
    if (!fin || inicio === fin) return formatearFechaEvento(inicio);
    return `${formatearFechaEvento(inicio)} - ${formatearFechaEvento(fin)}`;
}

function mapEventoParaDetalle(ev) {
    const pub  = ev.publicacion || {};
    const prog = ev.programacion || {};
    return {
        id: ev.id,
        titulo: pub.titulo || ev.nombre,
        contenido: pub.contenido || '',
        evento: ev.nombre,
        fecha: pub.fecha_publicacion ? formatearFechaEvento(pub.fecha_publicacion) : '',
        entrega: formatearRangoFechasEvento(prog.fecha_inicio, prog.fecha_fin),
        lugar: prog.lugar || 'No especificado',
        autor: pub.autor || '',
        estado: ev.estado,
        imagen: pub.imagen || '',
    };
}

function renderizarTarjetaEvento(ev) {
    const datos = mapEventoParaDetalle(ev);
    const { titulo, contenido, fecha: fechaPub, entrega: fecha, lugar, imagen } = datos;

    // Guardamos los datos en un atributo data- para evitar problemas con comillas
    const card = document.createElement('div');
    card.className = 'publicacion-card publicacion-activa api-evento-card';
    card.dataset.eventoId = ev.id;
    card.dataset.ev = JSON.stringify(datos);
    if (window.eventoAbiertoId && String(window.eventoAbiertoId) === String(ev.id)) {
        card.classList.add('seleccionada');
    }
    card.addEventListener('click', function() {
        document.querySelectorAll('.api-evento-card').forEach(c => c.classList.remove('seleccionada'));
        this.classList.add('seleccionada');
        window.eventoAbiertoId = ev.id;
        verDetallePublicacion(JSON.parse(this.dataset.ev));
    });

    card.innerHTML = `
        ${imagen ? `
        <div class="api-evento-img">
            <img src="${imagen}" alt="${titulo}" loading="lazy">
            <span class="publicacion-badge badge-activo api-live-badge">
                <i class="fa-solid fa-circle api-dot"></i> En vivo
            </span>
        </div>` : `
        <div class="api-evento-img api-evento-img--placeholder">
            <i class="fa-solid fa-calendar-star"></i>
            <span class="publicacion-badge badge-activo api-live-badge">
                <i class="fa-solid fa-circle api-dot"></i> En vivo
            </span>
        </div>`}

        <div class="publicacion-header" style="margin-top:12px">
            <span class="publicacion-fecha">
                <i class="fa-regular fa-calendar"></i> ${fechaPub || fecha}
            </span>
        </div>

        <div class="publicacion-body">
            <h3 class="publicacion-titulo">${titulo}</h3>
            <p class="publicacion-evento">
                <i class="fa-solid fa-tag"></i> ${ev.nombre}
            </p>
            <p class="publicacion-contenido">
                ${contenido.length > 100 ? contenido.substring(0, 100) + '…' : contenido}
            </p>
        </div>

        <div class="publicacion-footer" style="margin-top:auto;padding-top:12px;border-top:1px solid rgba(0,0,0,0.07)">
            <div style="display:flex;gap:12px;flex-wrap:wrap;font-size:0.82rem;color:var(--color-text-muted)">
                <span><i class="fa-solid fa-location-dot"></i> ${lugar}</span>
                <span><i class="fa-solid fa-truck"></i> ${fecha}</span>
            </div>
            <p class="publicacion-autor" style="margin-top:8px">
                Ver detalles <i class="fa-solid fa-plus"></i>
            </p>
        </div>`;

    return card;
}

async function cargarEventosAPI() {
    const contenedor = document.getElementById('eventos-api-grid');
    const contador   = document.getElementById('eventos-api-count');
    const spinner    = document.getElementById('eventos-api-spinner');
    if (!contenedor) return;

    try {
        const res  = await fetch(`${API_BASE}/eventos`);
        const json = await res.json();

        if (spinner) spinner.style.display = 'none';

        if (!json.success || !json.data || !json.data.length) {
            contenedor.innerHTML = `
                <div class="publicaciones-empty" style="grid-column:1/-1">
                    <i class="fa-regular fa-calendar-xmark"></i>
                    <p>No hay eventos activos en este momento.</p>
                </div>`;
            return;
        }

        if (contador) {
            contador.textContent = json.total;
            contador.style.display = 'inline-flex';
        }

        contenedor.innerHTML = '';
json.data.forEach(ev => contenedor.appendChild(renderizarTarjetaEvento(ev)));

    } catch (e) {
        if (spinner) spinner.style.display = 'none';
        contenedor.innerHTML = `
            <div class="publicaciones-empty" style="grid-column:1/-1">
                <i class="fa-solid fa-triangle-exclamation"></i>
                <p>No se pudieron cargar los eventos. Intenta de nuevo más tarde.</p>
            </div>`;
        console.warn('Error al cargar eventos desde API:', e);
    }
}