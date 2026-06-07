const admin = {

  async initDashboard() {

    const res = await fetch(
      '/api/admin/dashboard'
    );

    const data = await res.json();

    document.getElementById(
      'ventas_hoy'
    ).textContent =
      '$' + data.ventas_hoy.toFixed(2);

    document.getElementById(
      'premios_hoy'
    ).textContent =
      '$' + data.premios_hoy.toFixed(2);

    document.getElementById(
      'ganancia_hoy'
    ).textContent =
      '$' + data.ganancia_hoy.toFixed(2);

    document.getElementById(
      'jugadores'
    ).textContent =
      data.jugadores;
  }

};