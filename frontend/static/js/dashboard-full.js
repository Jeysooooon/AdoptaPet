// frontend/static/js/dashboard-full.js
// Dashboard SPA de AdoptaPet — roles, filtros, catálogo, donaciones,
// eventos (FullCalendar) y manejo amigable de sesión/token.

const CONFIG = {
  USERS_URL: 'http://localhost:48910',
  ADOPTIONS_URL: 'http://localhost:48911',
  DONATIONS_URL: 'http://localhost:48912',
  EVENTS_URL: 'http://localhost:48913',
  PETS_URL: 'http://localhost:48914',
  NOTIFS_URL: 'http://localhost:48915'
};

const TOKEN_KEY = 'adoptapet_token';
const PET_PLACEHOLDER = '/static/img/pet-placeholder.svg';
const PROTECTED_ROUTES = ['adoptions', 'notifications'];

// ============================================================
// Errores de autenticación (401/403) — se manejan aparte de los
// errores genéricos para nunca mostrar mensajes técnicos.
// ============================================================
class AuthError extends Error {
  constructor(message, status) {
    super(message);
    this.name = 'AuthError';
    this.status = status;
  }
}

// ---------- Sesión / JWT ----------
function decodeToken(token) {
  try { return JSON.parse(atob(token.split('.')[1])); } catch (e) { return null; }
}
function isTokenExpired(payload) {
  if (!payload || !payload.exp) return false;
  return (payload.exp * 1000) < Date.now();
}
function getToken() {
  return localStorage.getItem(TOKEN_KEY) || sessionStorage.getItem(TOKEN_KEY) || null;
}
function clearSession() {
  localStorage.removeItem(TOKEN_KEY);
  sessionStorage.removeItem(TOKEN_KEY);
}
// Devuelve el payload del usuario si hay token válido y vigente; si no, null
// (y limpia cualquier token vencido que hubiera quedado guardado).
function getCurrentUser() {
  const token = getToken();
  if (!token) return null;
  const payload = decodeToken(token);
  if (!payload || isTokenExpired(payload)) { clearSession(); return null; }
  return payload;
}
// Rol efectivo: 'invitado' | 'usuario' | 'admin'
function getRole() {
  const user = getCurrentUser();
  if (!user) return 'invitado';
  return user.rol || user.role || 'usuario';
}

// ---------- API helper (Authorization + FormData + errores de auth) ----------
async function apiFetch(method, url, body = null, useAuth = false) {
  const headers = { 'Accept': 'application/json' };
  if (body && !(body instanceof FormData)) headers['Content-Type'] = 'application/json';

  if (useAuth) {
    const token = getToken();
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
  try { json = text ? JSON.parse(text) : null; } catch (e) { json = text; }

  if (!res.ok) {
    // 401/403 nunca se muestran con el texto técnico del backend:
    // se homologan a un AuthError que activa el flujo de sesión.
    if (res.status === 401 || res.status === 403) {
      throw new AuthError('Sesión no válida o expirada', res.status);
    }
    const msg = (json && (json.error || json.message)) ? (json.error || json.message) : res.statusText;
    throw new Error(msg || `HTTP ${res.status}`);
  }
  return json;
}

// ---------- UI helpers ----------
function showAlert(message, type = 'info', timeout = 5000) {
  const container = document.getElementById('alert-container');
  if (!container) return;
  const id = `alert-${Date.now()}`;
  const div = document.createElement('div');
  div.id = id;
  div.className = `alert alert-${type} alert-dismissible fade show`;
  div.role = 'alert';
  div.innerHTML = `${escapeHtml(message)} <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>`;
  container.appendChild(div);
  if (timeout) setTimeout(() => { try { div.remove(); } catch (e) {} }, timeout);
}
function escapeHtml(s) { if (s === null || s === undefined) return ''; return String(s).replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;').replaceAll('"', '&quot;'); }

function openLoginModal(mode = 'login') {
  const modalEl = document.getElementById('authModal');
  if (!modalEl || typeof bootstrap === 'undefined') return;
  setAuthMode(mode);
  bootstrap.Modal.getOrCreateInstance(modalEl).show();
}

// Cambia el modal entre modo "login" y "register": título, botón, campo de
// nombre, pestañas y el texto del link de abajo.
function setAuthMode(mode) {
  const modeEl = document.getElementById('authMode');
  if (!modeEl) return;
  modeEl.value = mode;

  const nombreGroup = document.getElementById('authNombreGroup');
  const nombreInput = document.getElementById('authNombre');
  const title = document.getElementById('authModalTitle');
  const submit = document.getElementById('authSubmit');
  const switchLink = document.getElementById('switchToRegister');
  const tabLogin = document.getElementById('authTabLogin');
  const tabRegister = document.getElementById('authTabRegister');

  const isRegister = mode === 'register';

  if (nombreGroup) nombreGroup.classList.toggle('d-none', !isRegister);
  if (nombreInput) nombreInput.required = isRegister;
  if (title) title.textContent = isRegister ? 'Registro' : 'Iniciar sesión';
  if (submit) submit.textContent = isRegister ? 'Registrar' : 'Entrar';
  if (switchLink) switchLink.textContent = isRegister ? '¿Ya tienes cuenta? Inicia sesión' : '¿No tienes cuenta? Regístrate';
  if (tabLogin) tabLogin.classList.toggle('active', !isRegister);
  if (tabRegister) tabRegister.classList.toggle('active', isRegister);
}

// Empty state amigable para rutas protegidas (sin token o sesión vencida).
function renderAuthEmptyState(root, { title = 'Necesitas iniciar sesión', message = 'Inicia sesión para ver esta sección.' } = {}) {
  root.innerHTML = `
  <div class="empty-state text-center">
    <div class="empty-state-icon"><i class="bi bi-person-lock"></i></div>
    <h5 class="mb-2">${escapeHtml(title)}</h5>
    <p class="text-muted mb-4">${escapeHtml(message)}</p>
    <button class="btn btn-success" id="empty-state-login-btn"><i class="bi bi-box-arrow-in-right me-1"></i>Iniciar Sesión</button>
  </div>`;
  const btn = document.getElementById('empty-state-login-btn');
  if (btn) btn.addEventListener('click', openLoginModal);
}

// Se dispara ante cualquier AuthError: limpia la sesión, refresca el header
// y, si ocurrió en una petición de segundo plano (no en la carga inicial de
// una vista protegida), avisa suavemente y reabre el login.
function handleSessionExpired({ background = false } = {}) {
  const hadSession = !!getToken();
  clearSession();
  updateHeaderUser();
  applyRoleVisibility();
  if (background && hadSession) {
    showAlert('Tu sesión expiró. Inicia sesión nuevamente para continuar.', 'warning');
  }
  openLoginModal();
}

// ---------- Auth / header ----------
function updateHeaderUser() {
  const user = getCurrentUser();
  const nameEl = document.getElementById('user-name');
  const roleEl = document.getElementById('user-role');
  const btnLogin = document.getElementById('btn-login');
  const btnLogout = document.getElementById('btn-logout');

  if (!user) {
    if (nameEl) nameEl.textContent = 'Invitado';
    if (roleEl) roleEl.textContent = '-';
    if (btnLogin) { btnLogin.style.display = 'inline-block'; btnLogin.innerHTML = '<i class="bi bi-box-arrow-in-right me-1"></i>Iniciar Sesión / Registrarse'; }
    if (btnLogout) btnLogout.style.display = 'none';
  } else {
    if (nameEl) nameEl.textContent = user.nombre || user.correo || user.email || 'Usuario';
    if (roleEl) roleEl.textContent = user.rol || user.role || 'usuario';
    if (btnLogin) btnLogin.style.display = 'none';
    if (btnLogout) { btnLogout.style.display = 'inline-block'; btnLogout.innerHTML = '<i class="bi bi-box-arrow-right me-1"></i>Cerrar sesión'; }
  }
}

// Oculta pestañas protegidas para invitados (Adopciones / Notificaciones).
function applyRoleVisibility() {
  const role = getRole();
  document.querySelectorAll('.sidebar .nav-link').forEach(a => {
    const route = a.dataset.route;
    const item = a.closest('.nav-item') || a;
    const shouldHide = PROTECTED_ROUTES.includes(route) && role === 'invitado';
    item.style.display = shouldHide ? 'none' : '';
  });
}

async function handleLoginSubmit(e) {
  e.preventDefault();
  const email = document.getElementById('authEmail').value.trim();
  const password = document.getElementById('authPassword').value.trim();
  const nombre = (document.getElementById('authNombre')?.value || '').trim();
  const mode = document.getElementById('authMode').value || 'login';
  if (!email || !password) { showAlert('Correo y contraseña son requeridos', 'warning'); return; }
  if (mode === 'register' && !nombre) { showAlert('El nombre es requerido para registrarte', 'warning'); return; }
  try {
    if (mode === 'login') {
      const res = await apiFetch('POST', `${CONFIG.USERS_URL}/login`, { correo: email, password }, false);
      if (!res.token) throw new Error('No se recibió token');
      localStorage.setItem(TOKEN_KEY, res.token);
      showAlert('Autenticación correcta', 'success');
    } else {
      const res = await apiFetch('POST', `${CONFIG.USERS_URL}/registro`, { nombre: nombre || email.split('@')[0], correo: email, contrasena: password }, false);
      if (res.token) localStorage.setItem(TOKEN_KEY, res.token);
      showAlert('Usuario creado y autenticado', 'success');
    }
    updateHeaderUser();
    applyRoleVisibility();
    const modalEl = document.getElementById('authModal');
    const modal = bootstrap.Modal.getInstance(modalEl);
    if (modal) modal.hide();
    // Refresca la vista actual para reflejar el nuevo rol (botones admin, tabs, etc).
    const activeRoute = document.querySelector('.sidebar .nav-link.active');
    navigateTo(activeRoute ? activeRoute.dataset.route : 'pets');
  } catch (err) {
    if (err instanceof AuthError) { showAlert('Correo o contraseña incorrectos', 'danger'); }
    else { showAlert(err.message || 'Error autenticando', 'danger'); }
  }
}

// ============================================================
// Router / vistas
// ============================================================
function setActiveRoute(route) {
  document.querySelectorAll('.sidebar .nav-link').forEach(a => a.classList.toggle('active', a.dataset.route === route));
  document.getElementById('view-title').textContent = ({ pets: 'Mascotas', adoptions: 'Adopciones', donations: 'Donaciones', events: 'Eventos', notifications: 'Notificaciones', account: 'Mi Cuenta' }[route] || 'Dashboard');
}

function navigateTo(route) {
  setActiveRoute(route);
  const root = document.getElementById('view-root');
  root.innerHTML = '';

  // Rutas protegidas: si es invitado, ni siquiera se consulta la API.
  if (PROTECTED_ROUTES.includes(route) && getRole() === 'invitado') {
    renderAuthEmptyState(root, {
      title: 'Inicia sesión para continuar',
      message: route === 'adoptions'
        ? 'Debes iniciar sesión para ver tus solicitudes de adopción.'
        : 'Debes iniciar sesión para ver tus notificaciones.'
    });
    return;
  }

  if (route === 'pets') renderPetsView(root);
  else if (route === 'adoptions') renderAdoptionsView(root);
  else if (route === 'donations') renderDonationsView(root);
  else if (route === 'events') renderEventsView(root);
  else if (route === 'notifications') renderNotificationsView(root);
  else if (route === 'account') renderAccountView(root);
  else renderWelcome(root);
}

function renderWelcome(root) { root.innerHTML = `<div class="p-4"><h3 class="mb-3">Bienvenido a AdoptaPet</h3><p class="text-muted">Usa el menú lateral para navegar entre Mascotas, Adopciones, Donaciones, Eventos, Notificaciones y tu cuenta.</p></div>`; }

// ---------- Pets view (catálogo + filtros + rol) ----------
let allPetsCache = [];

async function renderPetsView(root) {
  setActiveRoute('pets');
  const isAdmin = getRole() === 'admin';
  root.innerHTML = `
  <div class="d-flex justify-content-between align-items-center mb-3 flex-wrap gap-2">
    <h4 class="m-0">Catálogo de Mascotas</h4>
    <div>
      <button class="btn btn-sm btn-outline-secondary me-2" id="refresh-pets" ${isAdmin ? '' : 'style="display:none"'}><i class="bi bi-arrow-clockwise me-1"></i>Actualizar</button>
      <button class="btn btn-sm btn-success" id="btn-new-pet" ${isAdmin ? '' : 'style="display:none"'}><i class="bi bi-plus-lg me-1"></i>Registrar Mascota</button>
    </div>
  </div>
  <div class="filter-bar mb-3">
    <select id="filter-especie" class="form-select form-select-sm">
      <option value="">Especie: todas</option>
      <option value="Perro">Perro</option>
      <option value="Gato">Gato</option>
      <option value="Otro">Otro</option>
    </select>
    <select id="filter-tamano" class="form-select form-select-sm">
      <option value="">Tamaño: todos</option>
      <option value="Pequeño">Pequeño</option>
      <option value="Mediano">Mediano</option>
      <option value="Grande">Grande</option>
    </select>
    <select id="filter-edad" class="form-select form-select-sm">
      <option value="">Edad: todas</option>
      <option value="cachorro">Cachorro (&lt; 1 año)</option>
      <option value="joven">Joven (1-3 años)</option>
      <option value="adulto">Adulto (&gt; 3 años)</option>
    </select>
  </div>
  <div id="pets-container" class="view-grid"></div>`;

  const refresh = document.getElementById('refresh-pets'); if (refresh) refresh.addEventListener('click', () => loadPetsInto(document.getElementById('pets-container'), true));
  const newPetBtn = document.getElementById('btn-new-pet'); if (newPetBtn) newPetBtn.addEventListener('click', () => showNewPetForm());
  ['filter-especie', 'filter-tamano', 'filter-edad'].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.addEventListener('change', applyPetFilters);
  });
  await loadPetsInto(document.getElementById('pets-container'), true);
}

function formatEdad(meses) {
  const m = Number(meses);
  if (Number.isNaN(m)) return '';
  if (m < 12) return `${m} mes${m === 1 ? '' : 'es'}`;
  const anios = Math.floor(m / 12);
  return `${anios} año${anios === 1 ? '' : 's'}`;
}

function petCardTemplate(p) {
  const badgeClass = (p.estado === 'Disponible') ? 'badge-available' : 'badge-locked';
  const tamano = p['tamaño'] || p.tamano || '';
  const edadTexto = formatEdad(p.edad_meses);
  const sexo = p.sexo || '';
  const foto = p.foto_url || PET_PLACEHOLDER;
  return `
  <div class="card pet-card">
    <img src="${escapeHtml(foto)}" class="card-img-top" alt="${escapeHtml(p.nombre)}" loading="lazy" onerror="this.onerror=null;this.src='${PET_PLACEHOLDER}';">
    <div class="card-body d-flex flex-column">
      <h5 class="card-title text-truncate mb-1">${escapeHtml(p.nombre)}</h5>
      <p class="text-muted small mb-2">${escapeHtml(p.especie || '')} • ${escapeHtml(p.raza || '')}</p>
      <div class="pet-badges mb-2">
        ${edadTexto ? `<span class="badge pet-badge"><i class="bi bi-calendar3 me-1"></i>${escapeHtml(edadTexto)}</span>` : ''}
        ${tamano ? `<span class="badge pet-badge"><i class="bi bi-arrows-angle-expand me-1"></i>${escapeHtml(tamano)}</span>` : ''}
        ${sexo ? `<span class="badge pet-badge"><i class="bi bi-gender-ambiguous me-1"></i>${escapeHtml(sexo)}</span>` : ''}
      </div>
      <p class="mb-3 small pet-description">${escapeHtml(p.descripcion || '')}</p>
      <div class="mt-auto d-flex justify-content-between align-items-center">
        <span class="badge ${badgeClass}">${escapeHtml(p.estado || '')}</span>
        <div>
          <button class="btn btn-sm btn-outline-primary me-2" data-action="view" data-id="${p.id_mascota}">Ver</button>
          <button class="btn btn-sm btn-success" data-action="adopt" data-id="${p.id_mascota}" ${p.estado !== 'Disponible' ? 'disabled' : ''}>Solicitar Adopción</button>
        </div>
      </div>
    </div>
  </div>`;
}

function petMatchesFilters(p) {
  const especie = document.getElementById('filter-especie')?.value || '';
  const tamano = document.getElementById('filter-tamano')?.value || '';
  const edadRango = document.getElementById('filter-edad')?.value || '';
  if (especie && (p.especie || '').toLowerCase() !== especie.toLowerCase()) return false;
  if (tamano && (p['tamaño'] || p.tamano || '').toLowerCase() !== tamano.toLowerCase()) return false;
  if (edadRango) {
    const meses = Number(p.edad_meses) || 0;
    if (edadRango === 'cachorro' && !(meses < 12)) return false;
    if (edadRango === 'joven' && !(meses >= 12 && meses <= 36)) return false;
    if (edadRango === 'adulto' && !(meses > 36)) return false;
  }
  return true;
}

function renderPetsList(container, pets) {
  if (!pets.length) {
    container.innerHTML = `
    <div class="empty-state text-center">
      <div class="empty-state-icon"><i class="bi bi-search"></i></div>
      <h5 class="mb-2">No hay mascotas con esos filtros</h5>
      <p class="text-muted mb-0">Prueba ajustando la especie, el tamaño o la edad.</p>
    </div>`;
    return;
  }
  container.innerHTML = pets.map(p => petCardTemplate(p)).join('');
  container.querySelectorAll('button[data-action]').forEach(btn => btn.addEventListener('click', onPetAction));
}

function applyPetFilters() {
  const container = document.getElementById('pets-container');
  if (!container) return;
  renderPetsList(container, allPetsCache.filter(petMatchesFilters));
}

async function loadPetsInto(container, refetch = false) {
  if (!container) return;
  container.innerHTML = '<div class="text-center text-muted p-4">Cargando mascotas...</div>';
  try {
    if (refetch || !allPetsCache.length) {
      const res = await apiFetch('GET', `${CONFIG.PETS_URL}/mascotas`);
      allPetsCache = res.mascotas || [];
    }
    applyPetFilters();
  } catch (err) {
    container.innerHTML = `<div class="text-danger p-3">No se pudo cargar el catálogo de mascotas. Intenta más tarde.</div>`;
  }
}

function onPetAction(e) { const btn = e.currentTarget; const action = btn.dataset.action; const id = btn.dataset.id; if (action === 'view') { showPetDetail(id); } if (action === 'adopt') requestAdoption(id); }

// ---------- Detalle de mascota (modal) ----------
function showPetDetail(id) {
  const p = allPetsCache.find(x => String(x.id_mascota) === String(id));
  if (!p) { showAlert('No se encontró la información de esta mascota.', 'warning'); return; }

  const modalId = 'petDetailModal';
  const existing = document.getElementById(modalId);
  if (existing) existing.remove();

  const badgeClass = (p.estado === 'Disponible') ? 'badge-available' : 'badge-locked';
  const tamano = p['tamaño'] || p.tamano || '';
  const edadTexto = formatEdad(p.edad_meses);
  const sexo = p.sexo || '';
  const foto = p.foto_url || PET_PLACEHOLDER;

  const html = `
  <div class="modal fade" id="${modalId}" tabindex="-1" aria-hidden="true">
    <div class="modal-dialog modal-dialog-centered">
      <div class="modal-content">
        <div class="modal-header">
          <h5 class="modal-title">${escapeHtml(p.nombre)}</h5>
          <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
        </div>
        <div class="modal-body">
          <img src="${escapeHtml(foto)}" class="pet-detail-photo mb-3" alt="${escapeHtml(p.nombre)}" onerror="this.onerror=null;this.src='${PET_PLACEHOLDER}';">
          <div class="d-flex justify-content-between align-items-center">
            <p class="text-muted mb-0">${escapeHtml(p.especie || '')} • ${escapeHtml(p.raza || '')}</p>
            <span class="badge ${badgeClass}">${escapeHtml(p.estado || '')}</span>
          </div>
          <div class="pet-detail-badges">
            ${edadTexto ? `<span class="badge pet-badge"><i class="bi bi-calendar3 me-1"></i>${escapeHtml(edadTexto)}</span>` : ''}
            ${tamano ? `<span class="badge pet-badge"><i class="bi bi-arrows-angle-expand me-1"></i>${escapeHtml(tamano)}</span>` : ''}
            ${sexo ? `<span class="badge pet-badge"><i class="bi bi-gender-ambiguous me-1"></i>${escapeHtml(sexo)}</span>` : ''}
          </div>
          <p class="mb-0">${escapeHtml(p.descripcion || 'Sin descripción disponible.')}</p>
        </div>
        <div class="modal-footer">
          <button type="button" class="btn btn-outline-secondary" data-bs-dismiss="modal">Cerrar</button>
          <button type="button" class="btn btn-success" id="petDetailAdoptBtn" ${p.estado !== 'Disponible' ? 'disabled' : ''}>Solicitar Adopción</button>
        </div>
      </div>
    </div>
  </div>`;
  document.body.insertAdjacentHTML('beforeend', html);
  const modalEl = document.getElementById(modalId);
  const modal = new bootstrap.Modal(modalEl);
  modal.show();
  modalEl.addEventListener('hidden.bs.modal', () => { try { modalEl.remove(); } catch (e) {} });
  document.getElementById('petDetailAdoptBtn').addEventListener('click', () => {
    modal.hide();
    requestAdoption(p.id_mascota);
  });
}

async function requestAdoption(id) {
  if (getRole() === 'invitado') { showAlert('Debes iniciar sesión para solicitar adopción', 'warning'); openLoginModal(); return; }
  const motivo = prompt('Motivo para la adopción:');
  if (!motivo) return;
  try {
    await apiFetch('POST', `${CONFIG.ADOPTIONS_URL}/adopciones`, { id_mascota: parseInt(id), motivo_adopcion: motivo }, true);
    showAlert('Solicitud de adopción enviada', 'success');
  } catch (err) {
    if (err instanceof AuthError) handleSessionExpired({ background: true });
    else showAlert('Error: ' + (err.message || ''), 'danger');
  }
  if (document.getElementById('pets-container')) loadPetsInto(document.getElementById('pets-container'), true);
}

// ---------- New Pet form (modal, solo admin) ----------
function showNewPetForm() {
  if (getRole() !== 'admin') { showAlert('Solo un administrador puede registrar mascotas', 'warning'); return; }
  const modalId = 'newPetModal';
  const existing = document.getElementById(modalId);
  if (existing) existing.remove();
  const html = `
  <div class="modal fade" id="${modalId}" tabindex="-1" aria-hidden="true">
    <div class="modal-dialog modal-lg modal-dialog-centered">
      <div class="modal-content">
        <div class="modal-header">
          <h5 class="modal-title">Registrar Mascota</h5>
          <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
        </div>
        <div class="modal-body">
          <form id="newPetForm">
            <div class="row g-3">
              <div class="col-md-6"><label class="form-label">Nombre</label><input id="petNombre" class="form-control" required></div>
              <div class="col-md-6"><label class="form-label">Especie</label><input id="petEspecie" class="form-control" required></div>
              <div class="col-md-6"><label class="form-label">Raza</label><input id="petRaza" class="form-control" required></div>
              <div class="col-md-3"><label class="form-label">Edad (meses)</label><input id="petEdadMeses" type="number" min="0" class="form-control" required></div>
              <div class="col-md-3"><label class="form-label">Tamaño</label>
                <select id="petTamano" class="form-select" required>
                  <option value="Pequeño">Pequeño</option>
                  <option value="Mediano">Mediano</option>
                  <option value="Grande">Grande</option>
                </select>
              </div>
              <div class="col-md-6"><label class="form-label">Estado</label><select id="petEstado" class="form-select"><option value="Disponible">Disponible</option><option value="En proceso">En proceso</option></select></div>
              <div class="col-12"><label class="form-label">Descripción</label><textarea id="petDescripcion" class="form-control" rows="3" required></textarea></div>
              <div class="col-md-8"><label class="form-label">Foto (URL)</label><input id="petFotoUrl" class="form-control" placeholder="https://..."></div>
              <div class="col-md-4 d-flex align-items-end"><button type="submit" class="btn btn-success w-100">Publicar Mascota</button></div>
            </div>
          </form>
        </div>
      </div>
    </div>
  </div>`;
  document.body.insertAdjacentHTML('beforeend', html);
  const modalEl = document.getElementById(modalId);
  const modal = new bootstrap.Modal(modalEl);
  modal.show();
  document.getElementById('newPetForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    await submitNewPet(modalEl);
  });
}

async function submitNewPet(modalEl) {
  const nombre = document.getElementById('petNombre').value.trim();
  const especie = document.getElementById('petEspecie').value.trim();
  const raza = document.getElementById('petRaza').value.trim();
  const edad_meses = document.getElementById('petEdadMeses').value;
  const tamano = document.getElementById('petTamano').value;
  const estado = document.getElementById('petEstado').value;
  const descripcion = document.getElementById('petDescripcion').value.trim();
  const foto_url = document.getElementById('petFotoUrl').value.trim();
  if (!nombre || !especie || !raza || edad_meses === '' || !descripcion) { showAlert('Completa los campos requeridos', 'warning'); return; }
  const payload = { nombre, especie, raza, edad_meses: parseInt(edad_meses, 10), 'tamaño': tamano, estado, descripcion };
  if (foto_url) payload.foto_url = foto_url;
  try {
    await apiFetch('POST', `${CONFIG.PETS_URL}/mascotas`, payload, true);
    showAlert('Mascota publicada correctamente', 'success');
    const bs = bootstrap.Modal.getInstance(modalEl);
    if (bs) bs.hide();
    setTimeout(() => { try { modalEl.remove(); } catch (e) {} }, 300);
    if (document.getElementById('pets-container')) loadPetsInto(document.getElementById('pets-container'), true);
  } catch (err) {
    if (err instanceof AuthError) handleSessionExpired({ background: true });
    else showAlert('Error publicando mascota: ' + (err.message || ''), 'danger');
  }
}

// ---------- Adopciones (protegida) ----------
function adoptionStatusBadgeClass(estado) {
  const e = (estado || '').toLowerCase();
  if (e === 'aprobado' || e === 'aprobada') return 'badge-aprobado';
  if (e === 'rechazado' || e === 'rechazada') return 'badge-rechazado';
  if (e === 'cancelado' || e === 'cancelada') return 'badge-cancelado';
  return 'badge-pendiente';
}

function formatFecha(iso) {
  if (!iso) return '';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return String(iso);
  return d.toLocaleDateString('es', { day: '2-digit', month: 'short', year: 'numeric' });
}

// Busca el nombre de la mascota en el catálogo ya cargado (si existe), para
// no mostrar solo "Mascota #ID".
function petNameById(id) {
  const p = allPetsCache.find(x => String(x.id_mascota) === String(id));
  return p ? p.nombre : null;
}

async function renderAdoptionsView(root) {
  setActiveRoute('adoptions');
  root.innerHTML = `<h4 class="mb-3">Mis solicitudes de adopción</h4><div id="adoptions-list"><div class="text-center text-muted p-4">Cargando solicitudes...</div></div>`;
  try {
    const res = await apiFetch('GET', `${CONFIG.ADOPTIONS_URL}/adopciones`, null, true);
    const items = res.solicitudes || res.adopciones || [];
    if (!items.length) {
      document.getElementById('adoptions-list').innerHTML = `
      <div class="empty-state text-center">
        <div class="empty-state-icon"><i class="bi bi-heart"></i></div>
        <h5 class="mb-2">Aún no tienes solicitudes</h5>
        <p class="text-muted mb-0">Ve al catálogo de Mascotas y solicita una adopción.</p>
      </div>`;
      return;
    }
    const rows = items.map(a => {
      const nombre = petNameById(a.id_mascota) || `Mascota #${a.id_mascota}`;
      const badgeClass = adoptionStatusBadgeClass(a.estado);
      return `
      <div class="adoption-item">
        <div>
          <div class="adoption-pet"><i class="bi bi-heart-fill text-danger me-2"></i>${escapeHtml(nombre)}</div>
          <div class="adoption-meta">${escapeHtml(a.motivo_adopcion || 'Sin motivo indicado')}</div>
          <div class="adoption-meta">Solicitada el ${formatFecha(a.fecha_solicitud)}</div>
        </div>
        <span class="badge ${badgeClass}">${escapeHtml(a.estado || 'Pendiente')}</span>
      </div>`;
    }).join('');
    document.getElementById('adoptions-list').innerHTML = rows;
  } catch (err) {
    if (err instanceof AuthError) { handleSessionExpired(); renderAuthEmptyState(root, { title: 'Tu sesión expiró', message: 'Vuelve a iniciar sesión para ver tus solicitudes de adopción.' }); }
    else document.getElementById('adoptions-list').innerHTML = `<div class="text-danger p-2">No se pudieron cargar tus solicitudes. Intenta más tarde.</div>`;
  }
}

// ---------- Donaciones ----------
async function loadDonationsHistory() {
  const container = document.getElementById('donationsList');
  if (!container) return;
  try {
    const res = await apiFetch('GET', `${CONFIG.DONATIONS_URL}/donaciones`);
    const items = (res.donaciones || []).slice().sort((a, b) => new Date(b.fecha) - new Date(a.fecha));
    if (!items.length) {
      container.innerHTML = `
      <div class="empty-state text-center">
        <div class="empty-state-icon"><i class="bi bi-heart"></i></div>
        <h5 class="mb-2">Aún no hay donaciones</h5>
        <p class="text-muted mb-0">Sé la primera persona en apoyar a las mascotas del refugio.</p>
      </div>`;
      return;
    }
    container.innerHTML = items.map(d => `
      <div class="donation-item">
        <div>
          <div class="donation-meta">${escapeHtml(d.comentario || 'Donación anónima')}</div>
          <div class="donation-meta">${formatFecha(d.fecha)}</div>
        </div>
        <span class="donation-amount">$${Number(d.monto).toFixed(2)}</span>
      </div>`).join('');
  } catch (err) {
    container.innerHTML = `<div class="text-danger p-2">No se pudo cargar el historial de donaciones.</div>`;
  }
}

function renderDonationsView(root) {
  setActiveRoute('donations');
  root.innerHTML = `
  <div class="d-flex justify-content-between align-items-center mb-3"><h4>Donaciones</h4></div>
  <div class="table-card">
    <form id="donationForm" class="row g-3">
      <div class="col-md-6"><label class="form-label">Nombre</label><input id="donorName" class="form-control" placeholder="Nombre" required></div>
      <div class="col-md-6">
        <label class="form-label">Monto (USD)</label>
        <input id="donorAmount" class="form-control" type="number" min="1" step="0.01" placeholder="Monto (USD)" required>
        <div class="quick-amounts mt-2">
          <button type="button" class="btn btn-sm btn-outline-success quick-amount-btn" data-amount="5">$5</button>
          <button type="button" class="btn btn-sm btn-outline-success quick-amount-btn" data-amount="10">$10</button>
          <button type="button" class="btn btn-sm btn-outline-success quick-amount-btn" data-amount="20">$20</button>
          <button type="button" class="btn btn-sm btn-outline-success quick-amount-btn" data-amount="50">$50</button>
        </div>
      </div>
      <div class="col-12"><label class="form-label">Mensaje (opcional)</label><textarea id="donorMessage" class="form-control" placeholder="Mensaje (opcional)"></textarea></div>
      <div class="col-12">
        <div class="payment-note"><i class="bi bi-shield-lock-fill me-2"></i>Serás redirigido a PayPal/Stripe para completar el pago de forma segura.</div>
      </div>
      <div class="col-12 text-end"><button class="btn btn-success" type="submit">Enviar Donación</button></div>
    </form>
  </div>
  <h5 class="mt-4 mb-3">Historial de donaciones</h5>
  <div id="donationsList"><div class="text-center text-muted p-4">Cargando historial...</div></div>`;

  loadDonationsHistory();

  root.querySelectorAll('.quick-amount-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      document.getElementById('donorAmount').value = btn.dataset.amount;
      root.querySelectorAll('.quick-amount-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
    });
  });

  const form = document.getElementById('donationForm');
  if (form) form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const name = document.getElementById('donorName').value.trim();
    const amount = parseFloat(document.getElementById('donorAmount').value);
    const message = document.getElementById('donorMessage').value.trim();
    if (!name || !amount) { showAlert('Nombre y monto son requeridos', 'warning'); return; }
    const user = getCurrentUser();
    const payload = { monto: amount, comentario: message ? `${name}: ${message}` : name };
    if (user && user.id) payload.id_usuario = user.id;
    try {
      await apiFetch('POST', `${CONFIG.DONATIONS_URL}/donaciones`, payload, !!user);
      showAlert('¡Gracias! Tu donación fue registrada. Ahora serás redirigido a la pasarela de pago.', 'success');
      form.reset();
      root.querySelectorAll('.quick-amount-btn').forEach(b => b.classList.remove('active'));
      loadDonationsHistory();
    } catch (err) {
      if (err instanceof AuthError) handleSessionExpired({ background: true });
      else showAlert(err.message || 'Ocurrió un error al registrar tu donación.', 'danger');
    }
  });
}

// ---------- Eventos (FullCalendar) ----------
let calendarInstance = null;

async function renderEventsView(root) {
  setActiveRoute('events');
  const isAdmin = getRole() === 'admin';
  root.innerHTML = `
    <div class="d-flex justify-content-between align-items-center mb-3 flex-wrap gap-2">
      <h4 class="m-0">Eventos</h4>
      ${isAdmin ? '<span class="small text-muted"><i class="bi bi-info-circle me-1"></i>Haz clic en un día del calendario para registrar un evento</span>' : ''}
    </div>
    <div class="table-card">
      <div id="events-calendar"></div>
      <div id="events-loose" class="mt-3"></div>
    </div>`;
  await loadEventsCalendar(isAdmin);
}

function parseEventDate(fecha) {
  if (!fecha) return null;
  const d = new Date(fecha);
  return Number.isNaN(d.getTime()) ? null : d;
}

async function loadEventsCalendar(isAdmin) {
  const el = document.getElementById('events-calendar');
  const looseEl = document.getElementById('events-loose');
  if (!el) return;
  el.innerHTML = '<div class="text-center text-muted p-4">Cargando eventos...</div>';
  if (looseEl) looseEl.innerHTML = '';
  try {
    const res = await apiFetch('GET', `${CONFIG.EVENTS_URL}/eventos`);
    const eventos = res.eventos || [];
    el.innerHTML = '';

    const calendarEvents = [];
    const looseEvents = [];
    eventos.forEach(e => {
      const d = parseEventDate(e.fecha_evento);
      if (d) {
        calendarEvents.push({ id: e.id_evento, title: e.titulo, start: d, extendedProps: { descripcion: e.descripcion, ubicacion: e.ubicacion } });
      } else {
        looseEvents.push(e); // fecha en texto libre no interpretable como fecha real
      }
    });

    if (typeof FullCalendar === 'undefined') {
      el.innerHTML = '<div class="text-danger p-3">No se pudo cargar el calendario de eventos.</div>';
      return;
    }

    if (calendarInstance) { calendarInstance.destroy(); calendarInstance = null; }
    calendarInstance = new FullCalendar.Calendar(el, {
      initialView: 'dayGridMonth',
      locale: 'es',
      height: 'auto',
      headerToolbar: { left: 'prev,next today', center: 'title', right: 'dayGridMonth,listMonth' },
      events: calendarEvents,
      eventClick: (info) => {
        const p = info.event.extendedProps;
        showAlert(`${info.event.title}${p.ubicacion ? ' — ' + p.ubicacion : ''}`, 'info', 6000);
      },
      dateClick: isAdmin ? (info) => showNewEventForm(info.dateStr) : undefined
    });
    calendarInstance.render();

    if (looseEl && looseEvents.length) {
      looseEl.innerHTML = `<div class="small text-muted mb-2">Otros eventos (fecha en formato libre):</div>` +
        looseEvents.map(e => `<div class="card mb-2 p-3"><strong>${escapeHtml(e.titulo)}</strong><div class="small text-muted">${escapeHtml(e.fecha_evento || '')} • ${escapeHtml(e.ubicacion || '')}</div><p class="mb-0">${escapeHtml(e.descripcion || '')}</p></div>`).join('');
    }
  } catch (err) {
    el.innerHTML = '<div class="text-danger p-3">No se pudieron cargar los eventos. Intenta más tarde.</div>';
  }
}

function showNewEventForm(dateStr) {
  if (getRole() !== 'admin') return;
  const modalId = 'newEventModal';
  const existing = document.getElementById(modalId); if (existing) existing.remove();
  const html = `
  <div class="modal fade" id="${modalId}" tabindex="-1" aria-hidden="true">
    <div class="modal-dialog modal-dialog-centered">
      <div class="modal-content">
        <div class="modal-header">
          <h5 class="modal-title">Registrar Evento</h5>
          <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
        </div>
        <div class="modal-body">
          <form id="newEventForm">
            <div class="mb-3"><label class="form-label">Título</label><input id="eventTitulo" class="form-control" required></div>
            <div class="mb-3"><label class="form-label">Fecha</label><input id="eventFecha" class="form-control" value="${escapeHtml(dateStr || '')}" required></div>
            <div class="mb-3"><label class="form-label">Ubicación</label><input id="eventUbicacion" class="form-control" required></div>
            <div class="mb-3"><label class="form-label">Descripción</label><textarea id="eventDescripcion" class="form-control" rows="3" required></textarea></div>
            <div class="d-grid"><button type="submit" class="btn btn-success">Publicar Evento</button></div>
          </form>
        </div>
      </div>
    </div>
  </div>`;
  document.body.insertAdjacentHTML('beforeend', html);
  const modalEl = document.getElementById(modalId);
  const modal = new bootstrap.Modal(modalEl);
  modal.show();
  document.getElementById('newEventForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const titulo = document.getElementById('eventTitulo').value.trim();
    const fecha_evento = document.getElementById('eventFecha').value.trim();
    const ubicacion = document.getElementById('eventUbicacion').value.trim();
    const descripcion = document.getElementById('eventDescripcion').value.trim();
    if (!titulo || !fecha_evento || !ubicacion || !descripcion) { showAlert('Todos los campos son requeridos', 'warning'); return; }
    try {
      await apiFetch('POST', `${CONFIG.EVENTS_URL}/eventos`, { titulo, fecha_evento, ubicacion, descripcion }, true);
      showAlert('Evento publicado correctamente', 'success');
      const bs = bootstrap.Modal.getInstance(modalEl);
      if (bs) bs.hide();
      setTimeout(() => { try { modalEl.remove(); } catch (e) {} }, 300);
      await loadEventsCalendar(true);
    } catch (err) {
      if (err instanceof AuthError) handleSessionExpired({ background: true });
      else showAlert('Error publicando evento: ' + (err.message || ''), 'danger');
    }
  });
}

// ---------- Notificaciones (protegida) ----------
async function renderNotificationsView(root) {
  setActiveRoute('notifications');
  root.innerHTML = `<h4 class="mb-3">Notificaciones</h4><div id="notifs"><div class="text-center text-muted p-4">Cargando notificaciones...</div></div>`;
  try {
    const res = await apiFetch('GET', `${CONFIG.NOTIFS_URL}/notificaciones`, null, true);
    const items = res.notificaciones || [];
    if (!items.length) {
      document.getElementById('notifs').innerHTML = `
      <div class="empty-state text-center">
        <div class="empty-state-icon"><i class="bi bi-bell"></i></div>
        <h5 class="mb-2">Tu bandeja está vacía</h5>
        <p class="text-muted mb-0">Aquí verás avisos sobre tus solicitudes de adopción y más.</p>
      </div>`;
      return;
    }
    document.getElementById('notifs').innerHTML = items.map(n => `
      <div class="notif-item ${n.leida ? 'read' : 'unread'}" data-id="${n.id_notificacion}">
        <i class="bi ${n.leida ? 'bi-envelope-open' : 'bi-envelope-fill'} notif-icon"></i>
        <div class="flex-fill">
          <div class="notif-msg">${escapeHtml(n.mensaje)}</div>
          <div class="notif-date">${formatFecha(n.fecha_creacion)}</div>
        </div>
        ${n.leida ? '' : '<span class="notif-unread-dot"></span>'}
      </div>`).join('');

    document.querySelectorAll('.notif-item.unread').forEach(el => {
      el.addEventListener('click', async () => {
        const id = el.dataset.id;
        try {
          await apiFetch('PUT', `${CONFIG.NOTIFS_URL}/notificaciones/${id}/leer`, {}, true);
          el.classList.remove('unread');
          el.classList.add('read');
          el.querySelector('.notif-icon').className = 'bi bi-envelope-open notif-icon';
          const dot = el.querySelector('.notif-unread-dot');
          if (dot) dot.remove();
        } catch (e) { /* si falla, se queda como no leída */ }
      });
    });
  } catch (err) {
    if (err instanceof AuthError) { handleSessionExpired(); renderAuthEmptyState(root, { title: 'Tu sesión expiró', message: 'Vuelve a iniciar sesión para ver tus notificaciones.' }); }
    else document.getElementById('notifs').innerHTML = `<div class="text-danger p-2">No se pudieron cargar tus notificaciones. Intenta más tarde.</div>`;
  }
}

// ---------- Mi Cuenta ----------
function renderAccountView(root) {
  setActiveRoute('account');
  const user = getCurrentUser();
  if (!user) { renderAuthEmptyState(root, { title: 'Inicia sesión', message: 'Inicia sesión para ver tu cuenta.' }); return; }
  root.innerHTML = `
  <div class="row">
    <div class="col-md-6"><div class="table-card"><h5>Perfil</h5><p><strong>${escapeHtml(user.nombre || user.correo || '')}</strong><br><span class="small text-muted">${escapeHtml(user.correo || '')}</span></p></div></div>
    <div class="col-md-6"><div class="table-card"><h5>Sesión</h5><p class="small text-muted">Rol: ${escapeHtml(user.rol || user.role || '-')}</p><div class="mt-2"><button class="btn btn-danger" id="btn-logout-account"><i class="bi bi-box-arrow-right me-1"></i>Cerrar sesión</button></div></div></div>
  </div>`;
  const out = document.getElementById('btn-logout-account');
  if (out) out.addEventListener('click', () => { clearSession(); updateHeaderUser(); applyRoleVisibility(); showAlert('Sesión cerrada', 'info'); navigateTo('pets'); });
}

// ============================================================
// Setup bindings
// ============================================================
function setupSidebar() {
  document.querySelectorAll('.sidebar .nav-link').forEach(a => {
    a.addEventListener('click', (e) => {
      e.preventDefault();
      navigateTo(a.dataset.route);
      if (window.innerWidth <= 768) document.querySelector('.sidebar').classList.remove('show');
    });
  });
  const toggle = document.getElementById('toggleSidebar');
  if (toggle) toggle.addEventListener('click', () => document.querySelector('.sidebar').classList.toggle('show'));
}

function setupAuthBindings() {
  const btnLogin = document.getElementById('btn-login');
  const btnLogout = document.getElementById('btn-logout');
  if (btnLogin) btnLogin.addEventListener('click', () => openLoginModal('login'));
  if (btnLogout) btnLogout.addEventListener('click', () => {
    clearSession(); updateHeaderUser(); applyRoleVisibility(); showAlert('Sesión cerrada', 'info'); navigateTo('pets');
  });
  const authForm = document.getElementById('authForm');
  if (authForm) authForm.addEventListener('submit', handleLoginSubmit);

  const switchLink = document.getElementById('switchToRegister');
  if (switchLink) switchLink.addEventListener('click', (e) => {
    e.preventDefault();
    const current = document.getElementById('authMode').value || 'login';
    setAuthMode(current === 'login' ? 'register' : 'login');
  });

  const tabLogin = document.getElementById('authTabLogin');
  const tabRegister = document.getElementById('authTabRegister');
  if (tabLogin) tabLogin.addEventListener('click', () => setAuthMode('login'));
  if (tabRegister) tabRegister.addEventListener('click', () => setAuthMode('register'));

  // Al cerrar el modal, siempre vuelve a modo login y limpia el formulario.
  const modalEl = document.getElementById('authModal');
  if (modalEl) modalEl.addEventListener('hidden.bs.modal', () => {
    document.getElementById('authForm').reset();
    setAuthMode('login');
  });
}

// init
document.addEventListener('DOMContentLoaded', () => {
  setupSidebar();
  setupAuthBindings();
  updateHeaderUser();
  applyRoleVisibility();
  navigateTo('pets');
});