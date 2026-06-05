const loterias = {
  init: async () => {
    const contenedor = document.getElementById('contenedor-loterias');
    if (!contenedor) return;

    try {
      const res = await fetch('/api/loterias');
      const data = await res.json();

      if (!data.loterias || data.loterias.length === 0) {
        contenedor.innerHTML = `<div class="col-12 text-center"><p>No hay loterías configuradas.</p></div>`;
        return;
      }

      contenedor.innerHTML = data.loterias.map(lot => {
        let badgeColor = 'bg-secondary';
        let botonDeshabilitado = 'disabled';

        if (lot.estado === 'abierta') {
          badgeColor = 'bg-success';
          botonDeshabilitado = '';
        } else if (lot.estado === 'cerrada') {
          badgeColor = 'bg-danger';
        } else if (lot.estado === 'resultado_pendiente') {
          badgeColor = 'bg-warning text-dark';
        } else if (lot.estado === 'procesada') {
          badgeColor = 'bg-info';
        }

        return `
          <div class="col-md-4 mb-3">
            <div class="card shadow-sm">
              <div class="card-body">
                <h5 class="card-title">${lot.nombre}</h5>
                <p class="card-text text-muted mb-1">Turno: ${lot.turno}</p>
                <p class="card-text small">Cierre: ${lot.hora_cierre}</p>
                <div class="d-flex justify-content-between align-items-center mt-3">
                  <span class="badge ${badgeColor}">${lot.estado.toUpperCase()}</span>
                  <button class="btn btn-sm btn-primary" ${botonDeshabilitado} onclick="alert('Ir a apostar a lotería ID: ' + ${lot.id})">Apostar</button>
                </div>
              </div>
            </div>
          </div>
        `;
      }).join('');

    } catch (err) {
      contenedor.innerHTML = `<div class="alert alert-danger">Error al cargar listado: ${err.message}</div>`;
    }
  }
};