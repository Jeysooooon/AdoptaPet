// frontend/static/js/app.js
// Módulo principal: gestión de peticiones y DOM
// Nota: usa fetch con async/await y localStorage para token JWT.

// Configuración de endpoints backend
const CONFIG = {
  USERS_URL: 'http://localhost:48910',
  PETS_URL: 'http://localhost:48914',
  ADOPTIONS_URL: 'http://localhost:48911'
};

const TOKEN_KEY = 'adoptapet_token';

// ---------- Helpers API ----------
async function apiFetch(method, url, body = null, useAuth = false) {
  const headers = { 'Accept': 'application/json' };
  if (body && !(body instanceof FormData)) headers['Content-Type'] = 'application/json';

  if (useAuth) {
    const token = localStorage.getItem(TOKEN_KEY) || sessionStorage.getItem(TOKEN_KEY) || null;
    if (token) headers['Authorization'] = 'Bearer ' + token;
  }

  const opts = { method, headers };
  const m = method ? method.toUpperCase() : 'GET';

  if (m === 'GET' || m === 'HEAD') {
    delete opts.body;
  } else if (body !== null && body !== undefined) {
    opts.body = body instanceof FormData ? body : JSON.stringify(body);
  }

  const res = await fetch(url, opts);
  const text = await res.text();
  let json = null;
  try { json = text ? JSON.parse(text) : null; } catch(e){ json = text; }
  if (!res.ok) {
    const msg = (json && (json.error || json.message)) ? (json.error || json.message) : res.statusText;
    throw new Error(msg || `HTTP ${res.status}`);
  }
  return json;
}
// ---------- UI Helpers ----------
function showAlert(message, type = 'info', timeout = 5000) {
  const container = document.getElementById('alert-container');
  const id = `alert-${Date.now()}`;
  const el = document.createElement('div');
  el.id = id;
  el.innerHTML = `
    <div class="alert alert-${type} alert-dismissible fade show" role="alert">
      ${message}
      <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    </div>`;
  container.appendChild(el);
  if (timeout) setTimeout(() => { try { el.remove(); } catch(e){} }, timeout);
}

function updateUserUI() {
  const token = localStorage.getItem(TOKEN_KEY);
  const userInfo = document.getElementById('user-info');
  const btnLogin = document.getElementById('btn-login');
  const btnLogout = document.getElementById('btn-logout');
  if (!token) {
    userInfo.textContent = '';
    btnLogin.style.display = '';
    btnLogout.style.display = 'none';
  } else {
    // intentar decodificar payload base64
    try {
      const payload = JSON.parse(atob(token.split('.')[1]));
      userInfo.textContent = `${payload.correo || payload.email} (${payload.rol || 'usuario'})`;
    } catch (e) {
      userInfo.textContent = 'Usuario';
    }
    btnLogin.style.display = 'none';
    btnLogout.style.display = '';
  }
}

// ---------- Login / Registro ----------
function openAuthModal(mode = 'login') {
  const authModal = new bootstrap.Modal(document.getElementById('authModal'));
  document.getElementById('authMode').value = mode;
  document.getElementById('authModalTitle').textContent = mode === 'login' ? 'Iniciar sesión' : 'Registro';
  document.getElementById('authSubmit').textContent = mode === 'login' ? 'Entrar' : 'Registrar';
  authModal.show();
}

async function handleAuthSubmit(e) {
  e.preventDefault();
  const mode = document.getElementById('authMode').value;
  const email = document.getElementById('authEmail').value.trim();
  const password = document.getElementById('authPassword').value.trim();
  if (!email || !password) { showAlert('Correo y contraseña obligatorios', 'warning'); return; }

  try {
    if (mode === 'login') {
      const res = await apiFetch('POST', `${CONFIG.USERS_URL}/login`, { correo: email, password }, false);
      const token = res.token;
      if (!token) throw new Error('No se recibió token');
      localStorage.setItem(TOKEN_KEY, token);
      updateUserUI();
      showAlert('Inicio de sesión correcto', 'success');
    } else {
      // registro
      const res = await apiFetch('POST', `${CONFIG.USERS_URL}/registro`, { nombre: email.split('@')[0], correo: email, contrasena: password }, false);
      if (res.token) {
        localStorage.setItem(TOKEN_KEY, res.token);
        updateUserUI();
      }
      showAlert('Registro exitoso', 'success');
    }
    // cerrar modal
    const modalEl = document.getElementById('authModal');
    const modal = bootstrap.Modal.getInstance(modalEl);
    modal.hide();
  } catch (err) {
    showAlert(err.message || 'Error en autenticación', 'danger');
  }
}

// ---------- Mascotas / Catálogo ----------
function createPetCard(p) {
  const col = document.createElement('div');
  col.className = 'col-sm-6 col-md-4 col-lg-3';
  col.innerHTML = `
    <div class="card h-100">
      <img src="${p.foto_url || '/static/img/placeholder.png'}" class="card-img-top" style="object-fit:cover; height:180px" alt="${p.nombre}">
      <div class="card-body d-flex flex-column">
        <h5 class="card-title">${escapeHtml(p.nombre)}</h5>
        <p class="card-text small text-muted mb-1">${escapeHtml(p.especie)} • ${escapeHtml(p.raza)}</p>
        <p class="card-text">${escapeHtml(p.descripcion || '')}</p>
        <div class="mt-auto d-flex justify-content-between align-items-center">
          <span class="badge bg-${p.estado === 'Disponible' ? 'success' : 'secondary'}">${p.estado}</span>
          <div>
            <button class="btn btn-sm btn-outline-primary me-2" data-action="view" data-id="${p.id_mascota}">Ver</button>
            <button class="btn btn-sm btn-success" data-action="adopt" data-id="${p.id_mascota}" ${p.estado !== 'Disponible' ? 'disabled' : ''}>Solicitar Adopción</button>
          </div>
        </div>
      </div>
    </div>
  `;
  // listeners
  col.querySelectorAll('button').forEach(btn => {
    btn.addEventListener('click', onPetButtonClick);
  });
  return col;
}

function escapeHtml(s) {
  if (!s) return '';
  return s.replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;');
}

async function loadPets() {
  try {
    const data = await apiFetch('GET', `${CONFIG.PETS_URL}/mascotas`);
    const grid = document.getElementById('pets-grid');
    grid.innerHTML = '';
    (data.mascotas || []).forEach(p => {
      grid.appendChild(createPetCard(p));
    });
  } catch (err) {
    showAlert('No se pudieron cargar mascotas: ' + (err.message || ''), 'danger', 8000);
  }
}

// ---------- Acciones sobre mascota (Solicitar adopción) ----------
async function onPetButtonClick(e) {
  const btn = e.currentTarget;
  const action = btn.dataset.action;
  const id = btn.dataset.id;
  if (action === 'view') {
    showAlert(`Ver mascota #${id} — implementar detalle si lo deseas`, 'info');
    return;
  }
  if (action === 'adopt') {
    // requerir token
    const token = localStorage.getItem(TOKEN_KEY);
    if (!token) {
      showAlert('Debes iniciar sesión para solicitar adopción', 'warning');
      openAuthModal('login');
      return;
    }
    const motivo = prompt('Escribe brevemente el motivo de adopción:');
    if (!motivo) { showAlert('Se requiere motivo', 'warning'); return; }
    try {
      await apiFetch('POST', `${CONFIG.ADOPTIONS_URL}/adopciones`, { id_mascota: parseInt(id), motivo_adopcion: motivo }, true);
      showAlert('Solicitud de adopción enviada', 'success');
      // actualizar lista de mascotas
      await loadPets();
    } catch (err) {
      showAlert('Error al solicitar adopción: ' + (err.message || ''), 'danger');
    }
  }
}

// ---------- Auth DOM wiring ----------
function setupAuthBindings() {
  document.getElementById('btn-login').addEventListener('click', () => openAuthModal('login'));
  document.getElementById('btn-logout').addEventListener('click', () => {
    localStorage.removeItem(TOKEN_KEY);
    updateUserUI();
    showAlert('Sesión cerrada', 'info');
  });
  document.getElementById('btn-refresh').addEventListener('click', () => loadPets());

  // modal form submission
  document.getElementById('authForm').addEventListener('submit', handleAuthSubmit);
  // switch link
  document.getElementById('switchToRegister').addEventListener('click', (e) => {
    e.preventDefault();
    const mode = document.getElementById('authMode').value;
    document.getElementById('authMode').value = mode === 'login' ? 'register' : 'login';
    document.getElementById('authModalTitle').textContent = mode === 'login' ? 'Registro' : 'Iniciar sesión';
    document.getElementById('authSubmit').textContent = mode === 'login' ? 'Registrar' : 'Entrar';
  });
}

// ---------- Inicialización ----------
document.addEventListener('DOMContentLoaded', () => {
  setupAuthBindings();
  updateUserUI();
  loadPets();
});
