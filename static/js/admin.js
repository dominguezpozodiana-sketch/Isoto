const admin = {
  // Inicializador para la vista del Dashboard Operativo
  initDashboard: async () => {
    await admin.cargarUsuariosDashboard();
  },

  // Inicializador para la vista de Control de Cajas y Billeteras
  initJugadores: async () => {
    await admin.cargarUsuariosBanca();
  },

  // Carga y dibuja los usuarios en el Dashboard Operativo
  cargarUsuariosDashboard: async () => {
    const tabla = document.getElementById('tabla-admin-usuarios');
    if (!tabla) return;

    try {
      const res = await fetch('/api/admin/usuarios');
      const data = await res.json();

      if (!data.usuarios || data.usuarios.length === 0) {
        tabla.innerHTML = `<tr><td colspan="5" class="text-center">No hay jugadores registrados en la plataforma.</td></tr>`;
        return;
      }

      tabla.innerHTML = data.usuarios.map(u => {
        const esBloqueado = u.estado === 'bloqueado';
        return `
          <tr>
            <td>${u.nombre}</td>
            <td>${u.telefono}</td>
            <td>$${u.saldo.toFixed(2)}</td>
            <td><span class="badge ${esBloqueado ? 'bg-danger' : 'bg-success'}">${u.estado.toUpperCase()}</span></td>
            <td>
              <button class="btn btn-sm ${esBloqueado ? 'btn-outline-success' : 'btn-outline-danger'}" 
                      onclick="admin.cambiarEstado('${u.telefono}', '${esBloqueado ? 'activo' : 'bloqueado'}')">
                ${esBloqueado ? 'Desbloquear' : 'Bloquear'}
              </button>
            </td>
          </tr>
        `;
      }).join('');
    } catch (err) {
      tabla.innerHTML = `<tr><td colspan="5" class="text-danger p-3">Error de comunicación con el servidor: ${err.message}</td></tr>`;
    }
  },

  // Envía el cambio de estado de un usuario (activo/bloqueado) al servidor
  cambiarEstado: async (telefono, estado) => {
    if (!confirm(`¿Estás seguro de que deseas cambiar el estado de este usuario a ${estado.toUpperCase()}?`)) return;

    const res = await fetch(`/api/admin/usuarios/${telefono}/cambiar-estado`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ estado: estado })
    });
    const data = await res.json();

    if (res.ok) {
      alert(data.msg);
      admin.cargarUsuariosDashboard();
    } else {
      alert(data.error);
    }
  },

  // Carga y dibuja los usuarios en la pestaña financiera de Cajas
  cargarUsuariosBanca: async () => {
    const tabla = document.getElementById('tabla-gestion-saldos');
    if (!tabla) return;

    try {
      const res = await fetch('/api/admin/usuarios');
      const data = await res.json();

      if (!data.usuarios || data.usuarios.length === 0) {
        tabla.innerHTML = `<tr><td colspan="5" class="text-center">No hay cuentas disponibles para transacciones.</td></tr>`;
        return;
      }

      tabla.innerHTML = data.usuarios.map(u => `
        <tr>
          <td><strong>${u.nombre}</strong></td>
          <td>${u.telefono}</td>
          <td class="text-success fw-bold">$${u.saldo.toFixed(2)}</td>
          <td><span class="badge ${u.estado === 'activo' ? 'bg-success' : 'bg-danger'}">${u.estado.toUpperCase()}</span></td>
          <td>
            <button class="btn btn-sm btn-success fw-bold" onclick="admin.abrirModalRecarga('${u.telefono}', '${u.nombre}')">
              💵 Gestionar Saldo
            </button>
          </td>
        </tr>
      `).join('');
    } catch (err) {
      tabla.innerHTML = `<tr><td colspan="5" class="text-danger p-3">Error al conectar con la banca: ${err.message}</td></tr>`;
    }
  },

  // Inyecta dinámicamente un modal limpio de Bootstrap en el DOM y gestiona el balance
  abrirModalRecarga: (telefono, nombre) => {
    const estructuraModal = `
      <div class="modal fade" id="modalFinanciero" tabindex="-1" aria-hidden="true">
        <div class="modal-dialog">
          <div class="modal-content">
            <div class="modal-header bg-success text-white">
              <h5 class="modal-title">Operación de Caja — ${nombre}</h5>
              <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
            </div>
            <div class="modal-body">
              <form id="form-movimiento-caja">
                <div class="mb-3">
                  <label class="form-label fw-bold">Tipo de Movimiento</label>
                  <select class="form-select" name="type" required>
                    <option value="credito">Cargar Saldo / Recargar (+)</option>
                    <option value="debito">Cobrar / Retirar Dinero (-)</option>
                  </select>
                </div>
                <div class="mb-3">
                  <label class="form-label fw-bold">Monto ($)</label>
                  <input type="number" step="0.01" class="form-control" name="amount" placeholder="0.00" required>
                </div>
                <div class="mb-3">
                  <label class="form-label fw-bold">Canal o Método de Transacción</label>
                  <select class="form-select" name="method" required>
                    <option value="efectivo">Efectivo / Cash</option>
                    <option value="zelle">Zelle</option>
                    <option value="pago_movil">Pago Móvil</option>
                    <option value="transferencia">Transferencia Bancaria</option>
                  </select>
                </div>
                <div class="mb-3">
                  <label class="form-label fw-bold">Observación interna</label>
                  <input type="text" class="form-control" name="desc" placeholder="Ej: Depósito por WhatsApp">
                </div>
                <button type="submit" class="btn btn-success w-100 fw-bold py-2">Confirmar e Inyectar</button>
              </form>
            </div>
          </div>
        </div>
      </div>
    `;

    // Evitar acumulaciones de modales anteriores en el árbol HTML
    const modalExistente = document.getElementById('modalFinanciero');
    if (modalExistente) modalExistente.remove();

    document.body.insertAdjacentHTML('beforeend', estructuraModal);
    const instanciaBootstrap = new bootstrap.Modal(document.getElementById('modalFinanciero'));
    instanciaBootstrap.show();

    // Capturar y procesar el formulario de forma asíncrona
    document.getElementById('form-movimiento-caja').onsubmit = async (e) => {
      e.preventDefault();
      const fData = new FormData(e.target);
      
      const payload = {
        monto: fData.get('amount'),
        tipo: fData.get('type'),
        metodo: fData.get('method'),
        descripcion: fData.get('desc')
      };

      const res = await fetch(`/api/admin/usuarios/${telefono}/recargar`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      const data = await res.json();

      if (res.ok) {
        alert(data.msg);
        instanciaBootstrap.hide();
        admin.cargarUsuariosBanca(); // Recarga la tabla de saldos de inmediato
      } else {
        alert(data.error);
      }
    };
  }
};