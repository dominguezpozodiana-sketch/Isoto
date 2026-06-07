const router = {
  rutas: {
    '/': {
      page: 'auth/login.html',
      init: () => {
        if (typeof auth !== 'undefined')
          auth.initLogin();
      }
    },

    '/registro': {
      page: 'auth/registro.html',
      init: () => {
        if (typeof auth !== 'undefined')
          auth.initRegistro();
      }
    },

    '/jugador/loterias': {
      page: 'jugador/loterias.html',
      init: () => {
        if (typeof loterias !== 'undefined')
          loterias.init();
      }
    },

    '/jugador/apostar': {
      page: 'jugador/apostar.html',
      init: () => {
        if (typeof jugadas !== 'undefined')
          jugadas.init();
      }
    },

    '/admin/dashboard': {
      page: 'admin/dashboard.html',
      init: () => {
        if (typeof admin !== 'undefined')
          admin.initDashboard();
      }
    },

    '/admin/jugadores': {
      page: 'admin/jugadores.html',
      init: () => {
        if (typeof admin !== 'undefined')
          admin.initJugadores();
      }
    },

    '/admin/resultados': {
      page: 'admin/resultados.html',
      init: () => {
        if (typeof resultados !== 'undefined')
          resultados.init();
      }
    },

    '/admin/reportes': {
      page: 'admin/reportes.html',
      init: () => {
        if (typeof reportes !== 'undefined')
          reportes.init();
      }
    }
  },

  init: () => {
    document.addEventListener('click', e => {
      if (e.target.matches('[data-link]')) {
        e.preventDefault();

        router.navegarA(
          e.target.getAttribute('href')
        );
      }
    });

    window.addEventListener(
      'popstate',
      () => {
        router.procesarRutaActual();
      }
    );

    router.procesarRutaActual();
  },

  navegarA: (url) => {
    history.pushState(null, null, url);
    router.procesarRutaActual();
  },

  procesarRutaActual: async () => {
    let ruta =
      window.location.pathname;

    const usuario = JSON.parse(
      localStorage.getItem('usuario') ||
      'null'
    );

    if (
      ruta.startsWith('/admin') &&
      (
        !usuario ||
        (
          usuario.rol !== 'dueno' &&
          usuario.rol !== 'admin'
        )
      )
    ) {
      ruta = '/';
    }

    const destino =
      router.rutas[ruta] ||
      router.rutas['/'];

    const contenedor =
      document.getElementById(
        'app-view'
      );

    if (!contenedor) return;

    try {
      const respuesta =
        await fetch(
          `/static/pages/${destino.page}`
        );

      const html =
        await respuesta.text();

      contenedor.innerHTML = html;

      if (destino.init) {
        destino.init();
      }

    } catch (err) {
      console.error(err);
    }
  }
};

document.addEventListener(
  'DOMContentLoaded',
  () => {
    router.init();
  }
);