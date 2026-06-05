const resultados = {
  // Inicializador del módulo de escrutinio
  init: async () => {
    await resultados.cargarLoteriasSelector();
    resultados.configurarFormulario();
  },

  // Rellena el listado de sorteos configurados en el sistema
  cargarLoteriasSelector: async () => {
    const selector = document.getElementById('res-loteria');
    if (!selector) return;

    try {
      const res = await fetch('/api/loterias');
      const data = await res.json();

      if (!data.loterias || data.loterias.length === 0) {
        selector.innerHTML = '<option value="">No hay loterías en el sistema</option>';
        return;
      }

      selector.innerHTML = data.loterias
        .map(l => `<option value="${l.id}">${l.nombre} (${l.turno.toUpperCase()})</option>`)
        .join('');
    } catch (err) {
      console.error("Error al cargar selector de resultados:", err);
    }
  },

  // Enlaza el evento de envío y despliega los resultados de la auditoría de premios
  configurarFormulario: () => {
    const form = document.getElementById('form-ingresar-resultados');
    const panelMetricas = document.getElementById('panel-reporte-escrutinio');

    if (!form) return;

    form.onsubmit = async (e) => {
      e.preventDefault();

      const payload = {
        loteria_id: document.getElementById('res-loteria').value,
        fecha: document.getElementById('res-fecha').value,
        pick3: document.getElementById('res-pick3').value,
        pick4: document.getElementById('res-pick4').value
      };

      try {
        const res = await fetch('/api/resultados', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });
        const data = await res.json();

        if (res.ok) {
          form.reset();
          
          // Mostrar reporte del dinero y boletas afectadas en la interfaz
          if (panelMetricas) {
            panelMetricas.classList.remove('d-none');
            panelMetricas.innerHTML = `
              <div class="alert alert-success border-0 shadow-sm rounded-3">
                <h5 class="fw-bold mb-2">🎉 ¡Escrutinio Finalizado Exitosamente!</h5>
                <ul class="mb-0 small">
                  <li><strong>Boletas Totales Evaluadas:</strong> ${data.procesadas}</li>
                  <li><strong>Tickets Premiados:</strong> ${data.ganadoras}</li>
                  <li><strong>Capital Total Desembolsado:</strong> $${data.monto_pagado.toFixed(2)}</li>
                </ul>
              </div>
            `;
          }
        } else {
          alert(data.error);
        }
      } catch (err) {
        alert("Error crítico de comunicación con el motor transaccional.");
      }
    };
  }
};