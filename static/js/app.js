/**
 * Enrutador Central del SPA (Single Page Application)
 * Maneja la navegación asíncrona, carga de plantillas HTML y ejecución de contenidos.
 */

const router = {
  // Definición oficial de rutas del sistema, sus vistas y funciones de inicialización
  rutas: {
    '/': {
      page: 'auth/login.html',
      init: () => { if (typeof auth !== 'undefined') auth.initLogin(); }
    },
    '/registro': {
      page: 'auth/registro.html',
      init: () => { if (typeof auth !== 'undefined') auth.initRegistro(); }
    },
    '/jugador/loterias': {
      page: 'jugador/loterias.html',
      init: () => { if (typeof loterias !== 'undefined') loterias.init(); }
    },
    '/jugador/apostar': {
      page: 'jugador/apostar.html',
      init: () => { if (typeof jugadas !== 'undefined') jugadas.init(); }
    },
    '/admin/dashboard': {
      page: 'admin/dashboard.html',
      init: () => { if (typeof admin !== 'undefined') admin.initDashboard(); }
    },
    '/admin/jugadores': {
      page: 'admin/jugadores.html',
      init: () => { if (typeof admin !== 'undefined') admin.initJugadores(); }
    },
    '/admin/resultados': {
      page: 'admin/resultados.html',
      init: () => { if (typeof resultados !== 'undefined') resultados.init(); }
    },
    '/admin/reportes': {
      page: 'admin/reportes.html',
      init: () => { if (typeof reportes !== 'undefined') reportes.init(); }
    }
  },

  // Inicializa el escuchador de cambios en la URL y carga la ruta inicial
  init: () => {
    document.addEventListener('click', e => {
      if (e.target.matches('[data-link]')) {
        e.preventDefault();
        router.navegarA(e.target.getAttribute('href'));
      }
    });

    window.addEventListener('popstate', () => {
      router.procesarRutaActual();
    });

    router.procesarRutaActual();
  },

  // Cambia la URL del navegador de forma lógica sin recargar la página
  navegarA: (url) => {
    window.history.pushState(null, null, url);
    router.procesarRutaActual();
  },

  // Resuelve la ruta actual, descarga el HTML correspondiente y ejecuta su JavaScript
  procesarRutaActual: async () => {
    let ruta = window.location.pathname;
    
    const destino = router.rutas[ruta] || router.rutas['/'];
    const contenedor = document.getElementById('app-view');

    if (!contenedor) {
      console.error("Error Crítico: No se encontró el contenedor principal con ID 'app-view'.");
      return;
    }

    try {
      const respuesta = await fetch(`/static/pages/${destino.page}`);
      
      if (!respuesta.ok) {
        throw new Error(`No se pudo cargar la vista: ${destino.page}`);
      }

      const htmlContenido = await respuesta.text();
      contenedor.innerHTML = htmlContenido;

      if (destino.init) {
        destino.init();
      }

    } catch (error) {
      console.error("Error en el enrutador SPA:", error);
      contenedor.innerHTML = `
        <div class="container mt-5 text-center">
          <div class="alert alert-danger shadow-sm">
            <h4 class="fw-bold">Error de Carga</h4>
            <p>Ocurrió un problema al renderizar este módulo. Por favor, recarga o contacta soporte.</p>
            <small class="text-muted">${error.message}</small>
          </div>
        </div>
      `;
    }
  }
};

// Iniciar el enrutador global cuando el DOM esté listo
document.addEventListener('DOMContentLoaded', () => {
  router.init();
});