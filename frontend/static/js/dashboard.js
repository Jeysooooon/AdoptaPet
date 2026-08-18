// frontend/static/js/dashboard.js - Dashboard edition
// Conecta con microservicios: Usuarios, Mascotas, Adopciones, Donaciones, Eventos, Notificaciones

const CONFIG = {
  USERS_URL: 'http://localhost:48910',
  ADOPTIONS_URL: 'http://localhost:48911',
  DONATIONS_URL: 'http://localhost:48912',
  EVENTS_URL: 'http://localhost:48913',
  PETS_URL: 'http://localhost:48914',
  NOTIFS_URL: 'http://localhost:48915'
};

const TOKEN_KEY = 'adoptapet_token';

// ---------- API helper ----------
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
// ---------- UI / Alerts ----------
function showAlert(message, type='info', timeout=5000){
  const container = document.getElementById('alert-container');
  if(!container) return;
  const id = `alert-${Date.now()}`;
  const div = document.createElement('div');
  div.id = id;
  div.className = `alert alert-${type} alert-dismissible fade show`;
  div.role = 'alert';
  div.innerHTML = `${escapeHtml(message)} <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>`;
  container.appendChild(div);
  if(timeout) setTimeout(()=>{ try{ div.remove(); }catch(e){} }, timeout);
}

function escapeHtml(s){ if(!s) return ''; return String(s).replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;'); }

// ---------- Auth UI ----------
function updateHeaderUser(){
  const token = localStorage.getItem(TOKEN_KEY);
  const nameEl = document.getElementById('user-name');
  const roleEl = document.getElementById('user-role');
  const btnLogin = document.getElementById('btn-login');
  const btnLogout = document.getElementById('btn-logout');
  if(!token){ nameEl.textContent = 'Invitado'; roleEl.textContent = '-'; if(btnLogin) btnLogin.style.display='inline-block'; if(btnLogout) btnLogout.style.display='none'; }
  else {
    try{
      const payload = JSON.parse(atob(token.split('.')[1]));
      if(nameEl) nameEl.textContent = payload.nombre || payload.correo || payload.email || 'Usuario';
      if(roleEl) roleEl.textContent = payload.rol || payload.role || 'usuario';
    }catch(e){ if(nameEl) nameEl.textContent='Usuario'; if(roleEl) roleEl.textContent='-'; }
    if(btnLogin) btnLogin.style.display='none'; if(btnLogout) btnLogout.style.display='inline-block';
  }
}

async function handleLoginSubmit(e){
  e.preventDefault();
  const email = document.getElementById('authEmail').value.trim();
  const password = document.getElementById('authPassword').value.trim();
  const mode = document.getElementById('authMode').value || 'login';
  if(!email || !password){ showAlert('Correo y contraseña son requeridos','warning'); return; }
  try{
    if(mode==='login'){
      const res = await apiFetch('POST', `${CONFIG.USERS_URL}/login`, { correo: email, password }, false);
      if(!res.token) throw new Error('No se recibió token');
      localStorage.setItem(TOKEN_KEY, res.token);
      updateHeaderUser();
      showAlert('Autenticación correcta','success');
    } else {
      const res = await apiFetch('POST', `${CONFIG.USERS_URL}/registro`, { nombre: email.split('@')[0], correo: email, contrasena: password }, false);
      if(res.token) localStorage.setItem(TOKEN_KEY, res.token);
      updateHeaderUser();
      showAlert('Usuario creado y autenticado','success');
    }
    const modalEl = document.getElementById('authModal');
    const modal = bootstrap.Modal.getInstance(modalEl);
    if(modal) modal.hide();
  }catch(err){ showAlert(err.message || 'Error autenticando','danger'); }
}

// ---------- Router / Views ----------
function setActiveRoute(route){
  document.querySelectorAll('.sidebar .nav-link').forEach(a=> a.classList.toggle('active', a.dataset.route===route));
  document.getElementById('view-title').textContent = ({pets:'Mascotas',adoptions:'Adopciones',donations:'Donaciones',events:'Eventos',notifications:'Notificaciones',account:'Mi Cuenta'}[route] || 'Dashboard');
}

function navigateTo(route){
  setActiveRoute(route);
  const root = document.getElementById('view-root');
  root.innerHTML = '';
  if(route==='pets') renderPetsView(root);
  else if(route==='adoptions') renderAdoptionsView(root);
  else if(route==='donations') renderDonationsView(root);
  else if(route==='events') renderEventsView(root);
  else if(route==='notifications') renderNotificationsView(root);
  else if(route==='account') renderAccountView(root);
  else renderWelcome(root);
}

// ---------- Views implementations ----------
function renderWelcome(root){
  root.innerHTML = `<div class="p-4">
    <h3 class="mb-3">Bienvenido a AdoptaPet</h3>
    <p class="text-muted">Usa el menú lateral para navegar entre Mascotas, Adopciones, Donaciones, Eventos, Notificaciones y tu cuenta.</p>
  </div>`;
}

async function renderPetsView(root){
  setActiveRoute('pets');
  root.innerHTML = `
    <div class="d-flex justify-content-between align-items-center mb-3">
      <h4 class="m-0">Catálogo de Mascotas</h4>
      <div>
        <button class="btn btn-sm btn-outline-secondary me-2" id="refresh-pets">Actualizar</button>
        <button class="btn btn-sm btn-success" id="btn-new-pet">Registrar Mascota</button>
      </div>
    </div>
    <div id="pets-container" class="view-grid"></div>`;
  document.getElementById('refresh-pets').addEventListener('click', ()=> loadPetsInto(document.getElementById('pets-container')));
  document.getElementById('btn-new-pet').addEventListener('click', ()=> showNewPetForm());
  await loadPetsInto(document.getElementById('pets-container'));
}

function petCardTemplate(p){
  const badgeClass = (p.estado==='Disponible')? 'badge-available' : 'badge-locked';
  return `
    <div class="card">
      <img src="${p.foto_url || '/static/img/placeholder.png'}" class="card-img-top" alt="${escapeHtml(p.nombre)}">
      <div class="card-body d-flex flex-column">
        <h5 class="card-title">${escapeHtml(p.nombre)}</h5>
        <p class="text-muted small mb-1">${escapeHtml(p.especie||'')} • ${escapeHtml(p.raza||'')}</p>
        <p class="mb-3">${escapeHtml(p.descripcion||'')}</p>
        <div class="mt-auto d-flex justify-content-between align-items-center">
          <span class="badge ${badgeClass}">${escapeHtml(p.estado||'')}</span>
          <div>
            <button class="btn btn-sm btn-outline-primary me-2" data-action="view" data-id="${p.id_mascota}">Ver</button>
            <button class="btn btn-sm btn-success" data-action="adopt" data-id="${p.id_mascota}" ${p.estado!=='Disponible' ? 'disabled' : ''}>Solicitar Adopción</button>
          </div>
        </div>
      </div>
    </div>`;
}

async function loadPetsInto(container){
  container.innerHTML = '<div class="text-center text-muted p-4">Cargando mascotas...</div>';
  try{
    const res = await apiFetch('GET', `${CONFIG.PETS_URL}/mascotas`);
    const pets = res.mascotas || [];
    container.innerHTML = pets.map(p=> petCardTemplate(p)).join('');
    // attach listeners
    container.querySelectorAll('button[data-action]').forEach(btn=> btn.addEventListener('click', onPetAction));
  }catch(err){ container.innerHTML = `<div class="text-danger p-3">Error cargando mascotas: ${escapeHtml(err.message||'')}</div>`; }
}

function onPetAction(e){
  const btn = e.currentTarget; const action = btn.dataset.action; const id = btn.dataset.id;
  if(action==='view'){ showAlert(`Ver detalle de mascota ${id}`,'info'); }
  if(action==='adopt') requestAdoption(id);
}

async function requestAdoption(id){
  const token = localStorage.getItem(TOKEN_KEY);
  if(!token){ showAlert('Debes iniciar sesión para solicitar adopción','warning'); const m = new bootstrap.Modal(document.getElementById('authModal')); m.show(); return; }
  const motivo = prompt('Motivo para la adopción:'); if(!motivo) return;
  try{ await apiFetch('POST', `${CONFIG.ADOPTIONS_URL}/adopciones`, { id_mascota: parseInt(id), motivo_adopcion: motivo }, true); showAlert('Solicitud de adopción enviada','success'); }
  catch(err){ showAlert('Error: '+(err.message||''),'danger'); }
  // refresh pets view
  if(document.getElementById('pets-container')) loadPetsInto(document.getElementById('pets-container'));
}

// ---------- Adoptions ----------
async function renderAdoptionsView(root){
  setActiveRoute('adoptions');
  root.innerHTML = `<div class="table-card"><h4>Mis solicitudes de adopción</h4><div id="adoptions-list">Cargando...</div></div>`;
  try{
    const res = await apiFetch('GET', `${CONFIG.ADOPTIONS_URL}/adopciones`, true);
    const items = res.solicitudes || res.adopciones || [];
    if(!items.length) { document.getElementById('adoptions-list').innerHTML = '<div class="text-muted p-3">No hay solicitudes.</div>'; return; }
    const rows = items.map(a=> `<div class="d-flex justify-content-between py-2 border-bottom"><div><strong>${escapeHtml(a.nombre_mascota || a.id_mascota || 'Mascota')}</strong><div class="small text-muted">${escapeHtml(a.motivo_adopcion || 'Sin motivo')}</div></div><div class="text-end small">${escapeHtml(a.estado || 'pendiente')}</div></div>`).join('');
    document.getElementById('adoptions-list').innerHTML = rows;
  }catch(err){ document.getElementById('adoptions-list').innerHTML = `<div class="text-danger p-2">${escapeHtml(err.message||'')}</div>`; }
}

// ---------- Donations ----------
function renderDonationsView(root){
  setActiveRoute('donations');
  root.innerHTML = `
    <div class="d-flex justify-content-between align-items-center mb-3"><h4>Donaciones</h4></div>
    <div class="table-card">
      <form id="donationForm" class="row g-3">
        <div class="col-md-6"><input id="donorName" class="form-control" placeholder="Nombre" required></div>
        <div class="col-md-6"><input id="donorAmount" class="form-control" type="number" placeholder="Monto (USD)" required></div>
        <div class="col-12"><textarea id="donorMessage" class="form-control" placeholder="Mensaje (opcional)"></textarea></div>
        <div class="col-12 text-end"><button class="btn btn-success" type="submit">Enviar Donación</button></div>
      </form>
      <div id="donationsList" class="mt-3"></div>
    </div>`;
  document.getElementById('donationForm').addEventListener('submit', async (e)=>{
    e.preventDefault();
    const name = document.getElementById('donorName').value.trim();
    const amount = parseFloat(document.getElementById('donorAmount').value);
    const message = document.getElementById('donorMessage').value.trim();
    if(!name || !amount) { showAlert('Nombre y monto son requeridos','warning'); return; }
    try{
      await apiFetch('POST', `${CONFIG.DONATIONS_URL}/donaciones`, { nombre: name, monto: amount, mensaje: message }, true);
      showAlert('Donación registrada','success');
    }catch(err){ showAlert(err.message||'Error','danger'); }
  });
}

// ---------- Events ----------
async function renderEventsView(root){
  setActiveRoute('events');
  root.innerHTML = `<h4>Eventos</h4><div id="eventsList">Cargando eventos...</div>`;
  try{
    const res = await apiFetch('GET', `${CONFIG.EVENTS_URL}/eventos`);
    const evs = res.eventos || [];
    if(!evs.length) { document.getElementById('eventsList').innerHTML = '<div class="text-muted p-3">No hay eventos.</div>'; return; }
    document.getElementById('eventsList').innerHTML = evs.map(e=> `<div class="card mb-2 p-3"><strong>${escapeHtml(e.titulo)}</strong><div class="small text-muted">${escapeHtml(e.fecha||'')}</div><p class="mb-0">${escapeHtml(e.descripcion||'')}</p></div>`).join('');
  }catch(err){ document.getElementById('eventsList').innerHTML = `<div class="text-danger p-2">${escapeHtml(err.message||'')}</div>`; }
}

// ---------- Notifications ----------
async function renderNotificationsView(root){
  setActiveRoute('notifications');
  root.innerHTML = `<h4>Notificaciones</h4><div id="notifs" class="mt-2">Cargando...</div>`;
  try{
    const res = await apiFetch('GET', `${CONFIG.NOTIFS_URL}/notificaciones`, true);
    const items = res.notificaciones || [];
    if(!items.length) { document.getElementById('notifs').innerHTML = '<div class="text-muted p-3">Sin notificaciones.</div>'; return; }
    document.getElementById('notifs').innerHTML = items.map(n=> `<div class="d-flex justify-content-between py-2 border-bottom"><div>${escapeHtml(n.titulo)}<div class="small text-muted">${escapeHtml(n.mensaje)}</div></div><div class="small text-muted">${escapeHtml(n.fecha||'')}</div></div>`).join('');
  }catch(err){ document.getElementById('notifs').innerHTML = `<div class="text-danger p-2">${escapeHtml(err.message||'')}</div>`; }
}

// ---------- Account ----------
function renderAccountView(root){
  setActiveRoute('account');
  const token = localStorage.getItem(TOKEN_KEY);
  let user = { nombre: 'Invitado', correo: '-' , rol: '-' };
  if(token){ try{ user = JSON.parse(atob(token.split('.')[1])); }catch(e){} }
  root.innerHTML = `
    <div class="row">
      <div class="col-md-6"><div class="table-card"><h5>Perfil</h5><p><strong>${escapeHtml(user.nombre||user.correo||'')}</strong><br><span class="small text-muted">${escapeHtml(user.correo||'')}</span></p></div></div>
      <div class="col-md-6"><div class="table-card"><h5>Sesión</h5><p class="small text-muted">Rol: ${escapeHtml(user.rol||'-')}</p><div class="mt-2"><button class="btn btn-danger" id="btn-logout-account">Cerrar sesión</button></div></div></div>
    </div>`;
  document.getElementById('btn-logout-account').addEventListener('click', ()=>{ localStorage.removeItem(TOKEN_KEY); updateHeaderUser(); showAlert('Sesión cerrada','info'); });
}

// ---------- Initialization and bindings ----------
function setupSidebar(){
  document.querySelectorAll('.sidebar .nav-link').forEach(a=>{
    a.addEventListener('click', (e)=>{ e.preventDefault(); const route = a.dataset.route; navigateTo(route); if(window.innerWidth<=768) document.querySelector('.sidebar').classList.remove('show'); });
  });
  const toggle = document.getElementById('toggleSidebar'); if(toggle) toggle.addEventListener('click', ()=> document.querySelector('.sidebar').classList.toggle('show'));
}

function setupAuthBindings(){
  const btnLogin = document.getElementById('btn-login'); const btnLogout = document.getElementById('btn-logout');
  if(btnLogin) btnLogin.addEventListener('click', ()=> new bootstrap.Modal(document.getElementById('authModal')).show());
  if(btnLogout) btnLogout.addEventListener('click', ()=>{ localStorage.removeItem(TOKEN_KEY); updateHeaderUser(); showAlert('Sesión cerrada','info'); });
  const authForm = document.getElementById('authForm'); if(authForm) authForm.addEventListener('submit', handleLoginSubmit);
  const switchLink = document.getElementById('switchToRegister'); if(switchLink) switchLink.addEventListener('click', (e)=>{ e.preventDefault(); const modeEl = document.getElementById('authMode'); modeEl.value = (modeEl.value==='login'?'register':'login'); document.getElementById('authModalTitle').textContent = modeEl.value==='login' ? 'Iniciar sesión' : 'Registro'; document.getElementById('authSubmit').textContent = modeEl.value==='login' ? 'Entrar' : 'Registrar'; });
}

// On load
document.addEventListener('DOMContentLoaded', ()=>{
  setupSidebar(); setupAuthBindings(); updateHeaderUser(); navigateTo('pets');
});
