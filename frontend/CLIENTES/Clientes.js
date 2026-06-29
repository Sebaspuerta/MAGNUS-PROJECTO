let todosLosClientes = [];

// ── MODAL OPEN/CLOSE ──────────────────────────────────────────────────────────
const modal      = document.getElementById("modal");
const btnAbrir   = document.getElementById("openModal");
const btnCerrar  = document.getElementById("closeModal");
const btnGuardar = document.getElementById("btn-guardar");

btnAbrir.addEventListener("click",  () => mostrarModalNuevo());
btnCerrar.addEventListener("click", () => cerrarModal());
window.addEventListener("click",    e  => { if (e.target === modal) cerrarModal(); });
btnGuardar.addEventListener("click",() => guardarCliente());

document.getElementById("searchInput").addEventListener("input", filtrarCards);

// ── INIT ───────────────────────────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => cargarClientes());

// ── CARGA ─────────────────────────────────────────────────────────────────────
async function cargarClientes() {
    setError("error-global", "");
    try {
        todosLosClientes = await window.api.apiRequest("/api/clients?include_inactive=true");
        renderStats(todosLosClientes);
        renderCards(todosLosClientes);
        renderTabla(todosLosClientes);
    } catch (err) {
        setError("error-global", "Error al cargar clientes: " + err.message);
        document.getElementById("clientesGrid").innerHTML =
            '<div style="color:#ef9a9a;">No se pudo cargar la lista.</div>';
    }
}

function renderStats(lista) {
    const activos   = lista.filter(c => c.is_active).length;
    setText("stat-total",     lista.length);
    setText("stat-activos",   activos);
    setText("stat-inactivos", lista.length - activos);
    setText("stat-deuda",     "—");
}

function filtrarCards() {
    const q = document.getElementById("searchInput").value.toLowerCase();
    const filtrados = todosLosClientes.filter(c =>
        c.full_name.toLowerCase().includes(q) ||
        (c.phone || "").toLowerCase().includes(q) ||
        (c.email || "").toLowerCase().includes(q)
    );
    renderCards(filtrados);
}

function renderCards(lista) {
    const grid    = document.getElementById("clientesGrid");
    const activos = lista.filter(c => c.is_active);

    if (!activos.length) {
        grid.innerHTML = '<div style="color:var(--muted);padding:20px 0;">No se encontraron clientes.</div>';
        return;
    }

    grid.innerHTML = activos.map(c => {
        const initials = c.full_name.split(" ").map(w => w[0]).join("").slice(0, 2).toUpperCase();
        return `<div class="cliente-card">
            <div class="cliente-header">
                <div class="avatar">${escHtml(initials)}</div>
                <div>
                    <h3>${escHtml(c.full_name)}</h3>
                    <span class="badge nuevo">Activo</span>
                </div>
            </div>
            <div class="cliente-info">
                ${c.phone  ? `<p><strong>Celular:</strong> ${escHtml(c.phone)}</p>` : ""}
                ${c.email  ? `<p><strong>Email:</strong> ${escHtml(c.email)}</p>`   : ""}
                ${c.document_number ? `<p><strong>Documento:</strong> ${escHtml(c.document_number)}</p>` : ""}
                ${c.notes  ? `<p><strong>Notas:</strong> ${escHtml(c.notes)}</p>`   : ""}
            </div>
            <div class="acciones">
                <button class="btn-info"      onclick="verPerfil(${c.id})">Perfil</button>
                <button class="btn-secondary" onclick="mostrarModalEditar(${c.id})">Editar</button>
                <button class="btn-danger"    onclick="desactivar(${c.id}, '${escAttr(c.full_name)}')">Desactivar</button>
            </div>
        </div>`;
    }).join("");
}

function renderTabla(lista) {
    const tbody = document.getElementById("tabla-body");
    if (!lista.length) {
        tbody.innerHTML = '<tr><td colspan="7" style="color:var(--muted);text-align:center;">Sin clientes registrados.</td></tr>';
        return;
    }
    tbody.innerHTML = lista.map(c => `<tr>
        <td>${c.id}</td>
        <td>${escHtml(c.full_name)}</td>
        <td>${c.phone   ? escHtml(c.phone)           : "—"}</td>
        <td>${c.email   ? escHtml(c.email)           : "—"}</td>
        <td>${c.document_number ? escHtml(c.document_number) : "—"}</td>
        <td>${c.is_active ? '<span class="badge nuevo" style="font-size:.72rem;">Activo</span>' : '<span class="badge inactivo" style="font-size:.72rem;">Inactivo</span>'}</td>
        <td><button class="btn-info" style="padding:5px 10px;font-size:.78rem;" onclick="verPerfil(${c.id})">Perfil</button></td>
    </tr>`).join("");
}

// ── MODAL CREAR / EDITAR ──────────────────────────────────────────────────────
function mostrarModalNuevo() {
    document.getElementById("modal-titulo").textContent = "Nuevo Cliente";
    document.getElementById("f-id").value               = "";
    document.getElementById("f-nombre").value           = "";
    document.getElementById("f-telefono").value         = "";
    document.getElementById("f-email").value            = "";
    document.getElementById("f-documento").value        = "";
    document.getElementById("f-nacimiento").value       = "";
    document.getElementById("f-notas").value            = "";
    setError("error-modal", "");
    btnGuardar.disabled    = false;
    btnGuardar.textContent = "Guardar Cliente";
    modal.classList.add("active");
}

async function mostrarModalEditar(id) {
    setError("error-modal", "");
    try {
        const c = await window.api.apiRequest(`/api/clients/${id}`);
        document.getElementById("modal-titulo").textContent = "Editar Cliente";
        document.getElementById("f-id").value               = c.id;
        document.getElementById("f-nombre").value           = c.full_name        || "";
        document.getElementById("f-telefono").value         = c.phone            || "";
        document.getElementById("f-email").value            = c.email            || "";
        document.getElementById("f-documento").value        = c.document_number  || "";
        document.getElementById("f-nacimiento").value       = c.birth_date       || "";
        document.getElementById("f-notas").value            = c.notes            || "";
        btnGuardar.disabled    = false;
        btnGuardar.textContent = "Guardar Cambios";
        modal.classList.add("active");
    } catch (err) {
        setError("error-global", "No se pudo cargar el cliente: " + err.message);
    }
}

function cerrarModal() { modal.classList.remove("active"); }

async function guardarCliente() {
    const id      = document.getElementById("f-id").value;
    const nombre  = document.getElementById("f-nombre").value.trim();
    const phone   = document.getElementById("f-telefono").value.trim()  || null;
    const email   = document.getElementById("f-email").value.trim()     || null;
    const doc     = document.getElementById("f-documento").value.trim() || null;
    const nac     = document.getElementById("f-nacimiento").value       || null;
    const notas   = document.getElementById("f-notas").value.trim()     || null;

    if (!nombre) { setError("error-modal", "El nombre es obligatorio."); return; }

    const body = { full_name: nombre, phone, email, document_number: doc, birth_date: nac, notes: notas };

    btnGuardar.disabled    = true;
    btnGuardar.textContent = "Guardando...";
    setError("error-modal", "");

    try {
        if (id) {
            await window.api.apiRequest(`/api/clients/${id}`, { method: "PATCH", body });
        } else {
            await window.api.apiRequest("/api/clients", { method: "POST", body });
        }
        cerrarModal();
        await cargarClientes();
    } catch (err) {
        setError("error-modal", err.message);
        btnGuardar.disabled    = false;
        btnGuardar.textContent = id ? "Guardar Cambios" : "Guardar Cliente";
    }
}

// ── DESACTIVAR ────────────────────────────────────────────────────────────────
async function desactivar(id, nombre) {
    if (!confirm(`¿Desactivar a ${nombre}?`)) return;
    setError("error-global", "");
    try {
        await window.api.apiRequest(`/api/clients/${id}/deactivate`, { method: "PATCH" });
        await cargarClientes();
    } catch (err) {
        setError("error-global", err.message);
    }
}

// ── PERFIL ────────────────────────────────────────────────────────────────────
async function verPerfil(id) {
    const box = document.getElementById("modal-perfil");
    document.getElementById("perfil-content").innerHTML = "Cargando...";
    box.classList.add("active");
    try {
        const p = await window.api.apiRequest(`/api/clients/${id}/profile`);
        document.getElementById("perfil-titulo").textContent = `Perfil — ${p.full_name}`;

        const badgeColor = {
            "VIP": "var(--purple)", "Frecuente": "var(--blue)",
            "Deudor": "var(--red)", "Inactivo": "var(--gray)", "Nuevo": "var(--green)"
        };
        const color = badgeColor[p.state] || "var(--gray)";

        document.getElementById("perfil-content").innerHTML = `
            <div class="perfil-row"><span class="lbl">Estado</span>
                <span class="val"><span style="background:${color};padding:3px 10px;border-radius:20px;font-size:.8rem;color:white;">${escHtml(p.state)}</span></span></div>
            <div class="perfil-row"><span class="lbl">Visitas</span><span class="val">${p.visits_count}</span></div>
            <div class="perfil-row"><span class="lbl">Total gastado</span><span class="val">${money(p.total_spent)}</span></div>
            <div class="perfil-row"><span class="lbl">Última visita</span><span class="val">${p.last_visit ? fmtFecha(p.last_visit) : "—"}</span></div>
            <div class="perfil-row"><span class="lbl">Saldo pendiente</span>
                <span class="val" style="color:${p.outstanding_balance > 0 ? '#ef9a9a' : '#81c784'};">${money(p.outstanding_balance)}</span></div>
        `;
    } catch (err) {
        document.getElementById("perfil-content").innerHTML = `<span style="color:#ef9a9a;">${err.message}</span>`;
    }
}

function cerrarPerfil() { document.getElementById("modal-perfil").classList.remove("active"); }

// ── UTILS ─────────────────────────────────────────────────────────────────────
function setText(id, val)  { const e = document.getElementById(id); if (e) e.textContent = val; }
function setError(id, msg) { const e = document.getElementById(id); if (e) e.textContent = msg; }
function money(n) {
    if (n == null) return "—";
    return "$ " + Number(n).toLocaleString("es-CO", { minimumFractionDigits: 0 });
}
function fmtFecha(iso) {
    if (!iso) return "—";
    return new Date(iso).toLocaleString("es-CO", { year:"numeric", month:"short", day:"numeric" });
}
function escHtml(s) {
    return String(s).replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;");
}
function escAttr(s) { return String(s).replace(/'/g, "\\'"); }
