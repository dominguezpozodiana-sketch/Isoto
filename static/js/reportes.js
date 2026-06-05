const reportes = {
  // Inicializador del módulo analítico
  init: async () => {
    await reportes.cargarMetricasCard();
    await reportes.cargarHistorialCompletoTickets();
  },

  // Consulta los ingresos, egresos y utilidades de la banca
  cargarMetricasCard: async () => {
    const txtIngresos = document.getElementById('rep-ingresos');
    const txtEgresos = document.getElementById('rep-egresos');
    const txtUtilidad = document.getElementById('rep-utilidad');
    const txtCustodia = document.getElementById('rep-custodia');

    if (!txtIngresos) return;

    try {
      const res = await fetch('/api/admin/dashboard-financiero');
      const data = await res.json();

      if (res.ok) {
        txtIngresos.innerText = `$${data.ingresos_apuestas.toFixed(2)}`;
        txtEgresos.innerText = `$${data.egresos_premios.toFixed(2)}`;
        txtUtilidad.innerText = `$${data.utilidad_neta.toFixed(2)}`;
        txtCustodia.innerText = `$${data.total_saldos_custodia.toFixed(2)}`;

        // Cambiar color visual de la utilidad si está en pérdidas o ganancias
        if (data.utilidad_neta >= 0) {
          txtUtilidad.className = "text-success fw-bold mb-0";
        } else {
          txtUtilidad.className = "text-danger fw-bold mb-0";
        }
      }
    } catch (err) {
      console.error("Error al renderizar balance financiero:", err);
    }
  },

  // Carga todas las apuestas del sistema en la vista de auditoría
  cargarHistorialCompletoTickets: async () => {
    const tabla = document.getElementById('tabla-reporte-tickets');
    if (!tabla) return;

    try {
      const res = await fetch('/api/admin/historial-tickets');
      const data = await res.json();

      if (!data.tickets || data.tickets.length === 0) {
        tabla.innerHTML = `<tr><td colspan="7" class="text-center">No se registran jugadas en la base de datos.</td></tr>`;
        return;
      }

      tabla.innerHTML = data.tickets.map(t => {
        let claseEstado = "bg-warning text-dark";
        if (t.estado === 'GANADA') claseEstado = "bg-success text-white";
        if (t.estado === 'PERDIDA') claseEstado = "bg-danger text-white";

        return `
          <tr>
            <td><span class="font-monospace fw-bold">${t.id}</span></td>
            <td>${t.jugador_telefono}</td>
            <td>${t.loteria}</td>
            <td><strong>${t.modalidad}</strong></td>
            <td class="text-center text-primary fw-bold">${t.numero}</td>
            <td>$${t.monto.toFixed(2)}</td>
            <td class="${t.monto_ganado > 0 ? 'text-success fw-bold' : 'text-muted'}">$${t.monto_ganado.toFixed(2)}</td>
            <td><span class="badge ${claseEstado}">${t.estado}</span></td>
          </tr>
        `;
      }).join('');
    } catch (err) {
      tabla.innerHTML = `<tr><td colspan="7" class="text-danger p-3">Fallo de comunicación: ${err.message}</td></tr>`;
    }
  }
};