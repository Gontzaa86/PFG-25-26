document.addEventListener('DOMContentLoaded', () => {
    const modalElem = document.getElementById('modalAulasAsignatura');
    if (modalElem) {
        window._modalAulas = new bootstrap.Modal(modalElem);
    }

    const btnGuardar = document.getElementById('btnGuardarAulas');
    if (btnGuardar) {
        btnGuardar.addEventListener('click', async () => {
            const cursoId = document.getElementById('cursoIdAulas').value;
            if (!cursoId) return alert('ID de asignatura no encontrado.');

            const checkboxes = Array.from(document.querySelectorAll('#contenedorAulasPorEdificio input[type="checkbox"]:checked'));
            const selected = checkboxes.map(cb => cb.value);

            try {
                const res = await fetch(`/api/asignaturas/${encodeURIComponent(cursoId)}/rooms`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ possible_rooms: selected })
                });

                const result = await res.json();
                if (!res.ok) {
                    alert(result.error || 'Error guardando aulas.');
                    return;
                }

                // Buscar TODAS las tarjetas que compartan esta asignatura en la página
                const cards = document.querySelectorAll(`[data-curso-id="${cursoId}"]`);

                cards.forEach(card => {
                    const badgeContainer = card.querySelector('.contenedor-badges-aulas');
                    const labelAulas = card.querySelector('.label-aulas');

                    if (badgeContainer) {
                        // Cambiar color del texto "Aulas:" según si tiene o no asignadas
                        if (labelAulas) {
                            labelAulas.className = selected.length ? 'text-muted me-1 label-aulas' : 'text-danger me-1 label-aulas';
                        }

                        // Limpiar SÓLO el contenedor de los badges en esta tarjeta
                        badgeContainer.innerHTML = '';

                        if (selected.length) {
                            selected.forEach(a => {
                                const span = document.createElement('span');
                                span.className = 'badge bg-light text-dark border-0 fw-normal';
                                span.style.fontSize = '0.7rem';
                                span.textContent = a;
                                badgeContainer.appendChild(span);
                            });
                        } else {
                            const span = document.createElement('span');
                            span.className = 'text-danger small';
                            span.textContent = 'Sin aulas asignadas';
                            badgeContainer.appendChild(span);
                        }
                    }
                });

                // Actualizar los datos locales en memoria para que persistan los cambios al reabrir el modal
                if (window.__GRADOS_ASIGNATURAS) {
                    const curso = window.__GRADOS_ASIGNATURAS.find(c => String(c.id) === String(cursoId));
                    if (curso) {
                        curso.possible_rooms = selected;
                    }
                }

                // Cerrar el modal de manera limpia
                if (window._modalAulas) {
                    window._modalAulas.hide();
                }

            } catch (err) {
                console.error('Error:', err);
                alert('Ocurrió un error al conectar con el servidor.');
            }
        });
    }
}); // <-- CORRECCIÓN: Aquí se cierra correctamente el DOMContentLoaded y el bloque principal

// CORRECCIÓN: La función ahora es externa y accesible globalmente
function abrirModalAulas(cursoId) {
    console.log('abrirModalAulas click ->', cursoId);
    
    if (!window._modalAulas) {
        const me = document.getElementById('modalAulasAsignatura');
        if (me) {
            try {
                window._modalAulas = new bootstrap.Modal(me);
            } catch (e) {
                console.error('No se pudo inicializar modal:', e);
            }
        }
    }
    
    const modal = window._modalAulas;
    document.getElementById('cursoIdAulas').value = cursoId;

    // Obtener datos globales
    const rooms = window.__GRADOS_ROOMS || [];
    const buildings = window.__GRADOS_BUILDINGS || [];
    const asignaturas = window.__GRADOS_ASIGNATURAS || [];

    // Buscar asignatura actual y sus aulas pre-seleccionadas
    const curso = asignaturas.find(c => String(c.id) === String(cursoId));
    const actuales = Array.isArray(curso && curso.possible_rooms) ? curso.possible_rooms : [];

    const cont = document.getElementById('contenedorAulasPorEdificio');
    if (!cont) {
        console.error('Contenedor de aulas no encontrado en DOM');
        return;
    }
    cont.innerHTML = '';

    // Agrupar aulas por edificio
    const mapa = {};
    rooms.forEach(r => {
        mapa[r.building] = mapa[r.building] || [];
        mapa[r.building].push(r);
    });

    const keys = buildings && buildings.length ? buildings : Object.keys(mapa);

    keys.forEach((edificio, idx) => {
        const aulasEd = mapa[edificio] || [];
        const itemId = `accordionEd-${idx}`;
        
        const card = document.createElement('div');
        card.className = 'accordion-item mb-2';

        const header = document.createElement('h2');
        header.className = 'accordion-header';
        header.id = `${itemId}-header`;

        const btn = document.createElement('button');
        btn.className = 'accordion-button collapsed d-flex justify-content-between align-items-center';
        btn.type = 'button';
        btn.setAttribute('data-bs-toggle', 'collapse');
        btn.setAttribute('data-bs-target', `#${itemId}-body`);
        btn.setAttribute('aria-expanded', 'false');
        btn.setAttribute('aria-controls', `${itemId}-body`);
        btn.innerHTML = `<span>${edificio} <small class='text-muted ms-2'>(${aulasEd.length} aulas)</small></span>`;

        const selectAllBtn = document.createElement('button');
        selectAllBtn.className = 'btn btn-sm btn-outline-secondary ms-3';
        selectAllBtn.type = 'button';
        selectAllBtn.textContent = 'Seleccionar todo';
        selectAllBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            const inputs = card.querySelectorAll('input[type="checkbox"]');
            const allChecked = Array.from(inputs).every(i => i.checked);
            inputs.forEach(i => i.checked = !allChecked);
        });

        const headerWrap = document.createElement('div');
        headerWrap.className = 'd-flex align-items-center w-100';
        headerWrap.appendChild(btn);
        headerWrap.appendChild(selectAllBtn);
        header.appendChild(headerWrap);

        const body = document.createElement('div');
        body.id = `${itemId}-body`;
        body.className = 'accordion-collapse collapse';
        body.setAttribute('aria-labelledby', `${itemId}-header`);

        const bodyInner = document.createElement('div');
        bodyInner.className = 'accordion-body';

        if (aulasEd.length === 0) {
            bodyInner.innerHTML = '<p class="text-muted small">No hay aulas registradas para este edificio.</p>';
        } else {
            aulasEd.forEach(a => {
                const div = document.createElement('div');
                div.className = 'form-check form-check-inline';

                const input = document.createElement('input');
                input.className = 'form-check-input';
                input.type = 'checkbox';
                input.id = `chk-${edificio}-${a.id}`;
                input.value = a.id;
                if (actuales.includes(a.id)) input.checked = true;

                const label = document.createElement('label');
                label.className = 'form-check-label';
                label.htmlFor = input.id;
                label.textContent = `${a.id} (${a.capacity || '-'})`;

                div.appendChild(input);
                div.appendChild(label);
                bodyInner.appendChild(div);
            });
        }

        body.appendChild(bodyInner);
        card.appendChild(header);
        card.appendChild(body);
        cont.appendChild(card);
    });

    try {
        if (modal) modal.show();
        else console.error('Modal no inicializado.');
    } catch (e) {
        console.error('Error mostrando modal:', e);
    }
}

// Exponer la función globalmente
window.abrirModalAulas = abrirModalAulas;