const auth = {
  initLogin: () => {
    const form = document.getElementById('login-form');
    if (!form) return;

    form.onsubmit = async (e) => {
      e.preventDefault();

      const formData = new FormData(form);
      const payload = Object.fromEntries(formData.entries());

      const res = await fetch('/api/auth/login', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(payload)
      });

      const data = await res.json();

      if (res.ok) {
        localStorage.setItem(
          'usuario',
          JSON.stringify(data.usuario)
        );

        if (
          data.usuario.rol === 'dueno' ||
          data.usuario.rol === 'admin'
        ) {
          router.navegarA('/admin/dashboard');
        } else {
          router.navegarA('/jugador/loterias');
        }
      } else {
        alert(data.error || 'Error al iniciar sesión');
      }
    };
  },

  initRegistro: () => {
    const form = document.getElementById('registro-form');
    if (!form) return;

    form.onsubmit = async (e) => {
      e.preventDefault();

      const formData = new FormData(form);
      const payload = Object.fromEntries(formData.entries());

      const res = await fetch('/api/auth/solicitar-registro', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(payload)
      });

      const data = await res.json();

      if (res.ok) {
        alert(data.msg);

        localStorage.setItem(
          'tel_verificar',
          payload.telefono
        );

        router.navegarA('/verificar');
      } else {
        alert(data.error || 'Error en registro');
      }
    };
  },

  initVerificar: () => {
    const form = document.getElementById('verificar-form');
    if (!form) return;

    const telGuardado =
      localStorage.getItem('tel_verificar');

    const campoTel =
      document.getElementById('v_tel');

    if (campoTel && telGuardado) {
      campoTel.value = telGuardado;
    }

    form.onsubmit = async (e) => {
      e.preventDefault();

      const formData = new FormData(form);
      const payload = Object.fromEntries(
        formData.entries()
      );

      const res = await fetch(
        '/api/auth/verificar-otp',
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify(payload)
        }
      );

      const data = await res.json();

      if (res.ok) {
        alert(data.msg);

        localStorage.removeItem(
          'tel_verificar'
        );

        router.navegarA('/');
      } else {
        alert(
          data.error || 'Código incorrecto'
        );
      }
    };
  },

  logout: async () => {
    localStorage.removeItem('usuario');
    router.navegarA('/');
  }
};

async function cargarHistorial() {
  const res = await fetch(
    '/api/jugadas/historial'
  );

  const data = await res.json();

  const tabla =
    document.getElementById(
      'tabla-historial'
    );

  if (!tabla) return;

  if (
    !data.historial ||
    data.historial.length === 0
  ) {
    tabla.innerHTML = `
      <tr>
        <td colspan="6" class="text-center">
          No hay apuestas registradas
        </td>
      </tr>
    `;
    return;
  }

  tabla.innerHTML = data.historial.map(j => `
    <tr>
      <td>${j.id}</td>
      <td>${j.modalidad.toUpperCase()}</td>
      <td>${j.numero_principal}${j.numero_parle ? ' - ' + j.numero_parle : ''}</td>
      <td>$${j.monto}</td>
      <td>${j.estado}</td>
      <td>$${j.monto_ganado}</td>
    </tr>
  `).join('');
}