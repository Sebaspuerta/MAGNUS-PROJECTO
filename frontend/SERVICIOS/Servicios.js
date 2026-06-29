let todosLosServicios = [];

// ── INIT ───────────────────────────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => cargarServicios());

// ── CARGA ─────────────────────────────────────────────────────────────────────
async function cargarServicios() {
    setError("error-global", "");
    const msg = document.getElementById("msg-carga");
    if (msg) msg.style.display = "block";

    try {
        todosLosServicios = await window.api.apiRequest("/api/services?include_inactive=true");
        if (msg) msg.style.display = "none";
        renderGrid(todosLosServicios);
    } catch (err) {
        if (msg) msg.textContent = "Error al cargar: " + err.message;
        setError("error-global", err.message);
    }
}

function filtrar() {
    const q = document.getElementById("search").value.toLowerCase();
    const filtrados = todosLosServicios.filter(s =>
        s.name.toLowerCase().includes(q) ||
        (s.category || "").toLowerCase().includes(q)
    );
    renderGrid(filtrados);
}

// ── RENDER GRID ────────────────────────────────────────────────────────────────
function renderGrid(lista) {
    const grid = document.getElementById("grid");

    if (!lista.length) {
        grid.innerHTML = '<div style="color:var(--muted);">No se encontraron servicios.</div>';
        return;
    }

    grid.innerHTML = lista.map(s => {
        const estadoClass = s.is_active ? "active" : "inactive";
        const estadoLabel = s.is_active ? "Activo"  : "Inactivo";
        const precio      = money(s.price);
        const duracion    = s.estimated_duration_minutes ? `⏱ ${s.estimated_duration_minutes} min` : "";
        const consumibles = s.uses_internal_consumables ? "🧴 Usa consumibles" : "";
        const categoria   = s.category || "Sin categoría";

        return `<div class="card">
            <h3>${escHtml(s.name)}</h3>
            <div class="meta" style="color:var(--gold);font-size:.78rem;">${escHtml(categoria)}</div>
            ${s.description ? `<div class="meta">${escHtml(s.description)}</div>` : ""}
            <div class="meta">💰 ${precio}${duracion ? " | " + duracion : ""}</div>
            ${consumibles ? `<div class="meta">${consumibles}</div>` : ""}

            <span class="badge ${estadoClass}">${estadoLabel}</span>

            <div class="actions">
                <button class="secondary" onclick="abrirModalEditar(${s.id})">Editar</button>
                ${s.is_active
                    ? `<button class="danger" onclick="desactivar(${s.id}, '${escAttr(s.name)}')">Desactivar</button>`
                    : `<span style="color:var(--muted);font-size:.78rem;align-self:center;">Inactivo</span>`
                }
            </div>
        </div>`;
    }).join("");
}

// ── MODAL ─────────────────────────────────────────────────────────────────────
function abrirModalNuevo() {
    document.getElementById("modal-titulo").textContent  = "Nuevo Servicio";
    document.getElementById("edit-id").value             = "";
    document.getElementById("name").value                = "";
    document.getElementById("category").value            = "";
    document.getElementById("desc").value                = "";
    document.getElementById("price").value               = "";
    document.getElementById("duration").value            = "";
    document.getElementById("uses-consumables").checked  = false;
    setError("error-modal", "");
    const btn = document.getElementById("btn-guardar");
    btn.disabled    = false;
    btn.textContent = "Guardar";
    document.getElementById("modal").classList.add("active");
}

async function abrirModalEditar(id) {
    setError("error-modal", "");
    try {
        const s = await window.api.apiRequest(`/api/services/${id}`);
        document.getElementById("modal-titulo").textContent  = "Editar Servicio";
        document.getElementById("edit-id").value             = s.id;
        document.getElementById("name").value                = s.name               || "";
        document.getElementById("category").value            = s.category           || "";
        document.getElementById("desc").value                = s.description        || "";
        document.getElementById("price").value               = s.price              ?? "";
        document.getElementById("duration").value            = s.estimated_duration_minutes ?? "";
        document.getElementById("uses-consumables").checked  = !!s.uses_internal_consumables;
        setError("error-modal", "");
        const btn = document.getElementById("btn-guardar");
        btn.disabled    = false;
        btn.textContent = "Guardar Cambios";
        document.getElementById("modal").classList.add("active");
    } catch (err) {
        setError("error-global", "No se pudo cargar el servicio: " + err.message);
    }
}

function cerrarModal() {
    document.getElementById("modal").classList.remove("active");
}

async function guardarServicio() {
    const id       = document.getElementById("edit-id").value;
    const nombre   = document.getElementById("name").value.trim();
    const categoria= document.getElementById("category").value || null;
    const desc     = document.getElementById("desc").value.trim()    || null;
    const precioRaw= document.getElementById("price").value;
    const durRaw   = document.getElementById("duration").value;
    const consums  = document.getElementById("uses-consumables").checked;

    if (!nombre) { setError("error-modal", "El nombre es obligatorio."); return; }

    const precio = parseFloat(precioRaw);
    if (isNaN(precio) || precio < 0) { setError("error-modal", "Ingresa un precio válido."); return; }

    const body = {
        name:                        nombre,
        category:                    categoria,
        description:                 desc,
        price:                       precio,
        estimated_duration_minutes:  durRaw ? parseInt(durRaw) : null,
        uses_internal_consumables:   consums,
    };

    const btn = document.getElementById("btn-guardar");
    btn.disabled    = true;
    btn.textContent = "Guardando...";
    setError("error-modal", "");

    try {
        if (id) {
            await window.api.apiRequest(`/api/services/${id}`, { method: "PATCH", body });
        } else {
            await window.api.apiRequest("/api/services", { method: "POST", body });
        }
        cerrarModal();
        await cargarServicios();
    } catch (err) {
        setError("error-modal", err.message);
        btn.disabled    = false;
        btn.textContent = id ? "Guardar Cambios" : "Guardar";
    }
}

// ── DESACTIVAR ────────────────────────────────────────────────────────────────
async function desactivar(id, nombre) {
    if (!confirm(`¿Desactivar el servicio "${nombre}"? Dejará de aparecer en Comandas.`)) return;
    setError("error-global", "");
    try {
        await window.api.apiRequest(`/api/services/${id}/deactivate`, { method: "PATCH" });
        await cargarServicios();
    } catch (err) {
        setError("error-global", err.message);
    }
}

// ── UTILS ─────────────────────────────────────────────────────────────────────
function setError(id, msg) { const e = document.getElementById(id); if (e) e.textContent = msg; }
function money(n) {
    if (n == null) return "—";
    return "$ " + Number(n).toLocaleString("es-CO", { minimumFractionDigits: 0 });
}
function escHtml(s) {
    return String(s).replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;");
}
function escAttr(s) { return String(s).replace(/'/g, "\\'"); }
