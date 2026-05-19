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

                // Actualizar badges en la tarjeta del curso sin recargar
                const card = document.querySelector(`[data-curso-id="${cursoId}"]`);
                if (card) {
                    const container = card.querySelector('.d-flex.flex-wrap.gap-1.align-items-center');
                    if (container) {
                        // Preserve the Edit button if present
                        const editBtn = container.querySelector('button');
                        const editBtnClone = editBtn ? editBtn.cloneNode(true) : null;

                        // Remover contenidos actuales y añadir nuevos badges
                        container.innerHTML = '';
                        const small = document.createElement('small');
                        small.className = selected.length ? 'text-muted me-1' : 'text-danger me-1';
                        small.style.fontSize = '0.75rem';
                        small.textContent = 'Aulas:';
                        container.appendChild(small);

                        if (selected.length) {
                            selected.forEach(a => {
                                const span = document.createElement('span');
                                span.className = 'badge bg-light text-dark border-0 fw-normal';
                                span.style.fontSize = '0.7rem';
                                span.textContent = a;
                                container.appendChild(span);
                            });
                        } else {
                            const span = document.createElement('span');
                            span.className = 'text-danger small';
                            span.textContent = 'Sin aulas asignadas';
                            container.appendChild(span);
                        }

                        // Reappend preserved edit button
                        if (editBtnClone) {
                            // Reattach the original onclick handler by ensuring the clone has the same onclick
                            container.appendChild(editBtnClone);
                            // Re-bind to global function if needed
                            try {
                                const onclickAttr = editBtnClone.getAttribute('onclick');
                                if (!onclickAttr) {
                                    // set onclick using cursoId
                                    editBtnClone.setAttribute('onclick', `abrirModalAulas('${cursoId}')`);
                                }
                            } catch (e) {
                                // ignore
                            }
                        }
                    }
                }

                    // Update in-memory asignaturas so modal reflects changes without recarga
                    try {
                        if (window.__GRADOS_ASIGNATURAS && Array.isArray(window.__GRADOS_ASIGNATURAS)) {
                            const idx = window.__GRADOS_ASIGNATURAS.findIndex(c => String(c.id) === String(cursoId));
                            if (idx !== -1) {
                                // Ensure we store a shallow copy of the array of strings
                                window.__GRADOS_ASIGNATURAS[idx].possible_rooms = Array.isArray(selected) ? selected.slice() : [];
                            }
                        }
                    } catch (e) {
                        console.warn('No se pudo actualizar cache local de asignaturas:', e);
                    }

                    if (window._modalAulas) window._modalAulas.hide();
            } catch (err) {
                console.error(err);
                alert('Error conectando con el servidor.');
            }
        });
    }
});

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

    // Obtener listado global de aulas y asignaturas (inyectadas en plantilla)
    const rooms = window.__GRADOS_ROOMS || [];
    const buildings = window.__GRADOS_BUILDINGS || [];
    const asignaturas = window.__GRADOS_ASIGNATURAS || [];

    // Buscar la asignatura para obtener posibles aulas actuales
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

    // Si no hay edificios, inferir desde rooms
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
            // Toggle: if all selected then unselect, else select all
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

// Exponer la función globalmente para que el onclick en la plantilla funcione
window.abrirModalAulas = abrirModalAulas;
