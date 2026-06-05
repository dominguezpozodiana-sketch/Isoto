const jugadas = {
  // Inicializador que se ejecuta al renderizar la vista de apuestas
  init: async () => {
    await jugadas.cargarLoteriasDisponibles();
    jugadas.configurarEventosFormulario();
  },

  // Busca e inyecta las loterias activas dentro del selector del formulario
  cargarLoteriasDisponibles: async () => {
    const selector = document.getElementById('apuesta-loteria');
    if (!selector) return;

    try {
      const res = await fetch('/api/loterias');
      const data = await res.json();

      if (!data.loterias || data.loterias.length === 0) {
        selector.innerHTML = '<option value="">No hay loterías abiertas</option>';
        return;
      }

      selector.innerHTML = data.loterias
        .filter(l => l.activa)
        .map(l => `<option value="${l.id}">${l.nombre} (${l.turno.toUpperCase()})</option>`)
        .join('');
    } catch (err) {
      console.error("Error al obtener loterías:", err);
    }
  },

  // Configura los escuchadores de eventos interactivos en la interfaz
  configurarEventosFormulario: () => {
    const selectModalidad = document.getElementById('apuesta-modalidad');
    const contenedorParle = document.getElementById('contenedor-segundo-numero');
    const inputMonto = document.getElementById('apuesta-monto');
    const txtGanancia = document.getElementById('ganancia-estimada');
    const form = document.getElementById('form-efectuar-apuesta');

    if (!selectModalidad || !form) return;

    // Cuotas quemadas del lado del cliente únicamente para el cálculo visual interactivo
    const cuotasVisuales = { fijo: 80, corrido: 25, parle: 1000 };

    // Muestra u oculta el campo del segundo número si se elige Parlé
    selectModalidad.addEventListener('change', (e) => {
      if (e.target.value === 'parle') {
        contenedorParle.classList.remove('d-none');
        document.getElementById('apuesta-num2').setAttribute('required', 'required');
      } else {
        contenedorParle.classList.add('d-none');
        document.getElementById('apuesta-num2').removeAttribute('required');
      }
      calcularPremio();
    });

    // Escucha el cambio de monto para computar la ganancia estimada en vivo
    inputMonto.addEventListener('input', calcularPremio);

    function calcularPremio() {
      const mod = selectModalidad.value;
      const monto = parseFloat(inputMonto.value) || 0;
      const multiplicador = cuotasVisuales[mod] || 0;
      txtGanancia.innerText = (monto * multiplicador).toFixed(2);
    }

    // Procesa el envío asíncrono del ticket al servidor
    form.onsubmit = async (e) => {
      e.preventDefault();

      const payload = {
        loteria_id: document.getElementById('apuesta-loteria').value,
        modalidad: selectModalidad.value,
        numero_principal: document.getElementById('apuesta-num1').value,
        numero_parle: selectModalidad.value === 'parle' ? document.getElementById('apuesta-num2').value : null,
        monto: inputMonto.value
      };

      try {
        const res = await fetch('/api/jugador/apostar', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });
        const data = await res.json();

        if (res.ok) {
          alert(`¡Apuesta registrada!\nTicket ID: ${data.ticket}\nNuevo Saldo: $${data.nuevo_saldo.toFixed(2)}`);
          form.reset();
          contenedorParle.classList.add('d-none');
          txtGanancia.innerText = '0.00';
        } else {
          alert(data.error);
        }
      } catch (err) {
        alert("Ocurrió un error de red al intentar registrar el ticket.");
      }
    };
  }
};