// ── MODAL OPEN/CLOSE (mantiene el patrón del CSS existente) ───────────────────
const modal      = document.getElementById("modal");
const btnAbrir   = document.getElementById("openModal");
const btnCerrar  = document.getElementById("closeModal");
const btnGuardar = document.getElementById("btn-guardar");

btnAbrir.addEventListener("click", () => mostrarModalNuevo());
btnCerrar.addEventListener("click", () => cerrarModal());
window.addEventListener("click", e => { if (e.target === modal) cerrarModal(); });
btnGuardar.addEventListener("click", () => guardarBarbero());

// ── INIT ───────────────────────────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => cargarBarberos());

// ── CARGA ─────────────────────────────────────────────────────────────────────
async function cargarBarberos() {
    setError("error-global", "");
    try {
        const lista = await window.api.apiRequest("/api/barbers?include_inactive=true");
        renderStats(lista);
        renderCards(lista);
        renderTabla(lista);
    } catch (err) {
        setError("error-global", "Error al cargar barberos: " + err.message);
        document.getElementById("barberos-grid").innerHTML =
            '<div style="color:#ef9a9a;">No se pudo cargar la lista.</div>';
    }
}

function renderStats(lista) {
    const activos   = lista.filter(b => b.is_active).length;
    const inactivos = lista.length - activos;
    setText("stat-activos",   activos);
    setText("stat-inactivos", inactivos);
    setText("stat-total",     lista.length);
}

function renderCards(lista) {
    const grid = document.getElementById("barberos-grid");
    const activos = lista.filter(b => b.is_active);
    const isOwner = ((window.api.getAuthUser() || {}).username || "").toLowerCase() === "mateo";

    if (!activos.length) {
        grid.innerHTML = '<div style="color:#9aa4b2;padding:20px 0;">No hay barberos activos.</div>';
        return;
    }

    grid.innerHTML = activos.map(b => {
        const initials = b.full_name.split(" ").map(w => w[0]).join("").slice(0, 2).toUpperCase();
        const comision = b.commission_type === "porcentaje"
            ? `${b.commission_value}%`
            : `$${Number(b.commission_value).toLocaleString("es-CO")} fijo`;

        const esMateo = (b.user_username || "").toLowerCase() === "mateo" ||
            b.full_name.toLowerCase().split(/\s+/).includes("mateo");

        const btnEliminar = isOwner && !esMateo
            ? `<button class="btn-danger" onclick="eliminarBarbero(${b.id}, '${escAttr(b.full_name)}')">Eliminar</button>`
            : "";

        return `<div class="barbero-card">
            <div class="barbero-header">
                <div class="avatar">${escHtml(initials)}</div>
                <div>
                    <h3>${escHtml(b.full_name)}</h3>
                    <span class="estado activo">Activo</span>
                </div>
            </div>
            <div class="datos">
                ${b.alias   ? `<p><strong>Alias:</strong> ${escHtml(b.alias)}</p>` : ""}
                ${b.phone   ? `<p><strong>Teléfono:</strong> ${escHtml(b.phone)}</p>` : ""}
                <p><strong>Comisión:</strong> ${escHtml(comision)}</p>
                ${b.notes   ? `<p><strong>Notas:</strong> ${escHtml(b.notes)}</p>` : ""}
            </div>
            <div class="acciones">
                <button class="btn-info"      onclick="verRendimiento(${b.id})">Rendimiento</button>
                <button class="btn-secondary" onclick="mostrarModalEditar(${b.id})">Editar</button>
                <button class="btn-danger"    onclick="desactivar(${b.id}, '${escAttr(b.full_name)}')">Desactivar</button>
                ${btnEliminar}
            </div>
        </div>`;
    }).join("");
}

function renderTabla(lista) {
    const tbody = document.getElementById("tabla-body");
    if (!lista.length) {
        tbody.innerHTML = '<tr><td colspan="6" style="color:#9aa4b2;text-align:center;">Sin barberos registrados.</td></tr>';
        return;
    }
    tbody.innerHTML = lista.map(b => {
        const comision = b.commission_type === "porcentaje"
            ? `${b.commission_value}%`
            : `$${Number(b.commission_value).toLocaleString("es-CO")}`;
        const estadoClass = b.is_active ? "activo" : "inactivo";
        const estadoLabel = b.is_active ? "Activo" : "Inactivo";
        return `<tr>
            <td>${b.id}</td>
            <td>${escHtml(b.full_name)}</td>
            <td>${b.alias ? escHtml(b.alias) : "—"}</td>
            <td>${b.phone ? escHtml(b.phone) : "—"}</td>
            <td>${escHtml(comision)}</td>
            <td><span class="estado ${estadoClass}">${estadoLabel}</span></td>
        </tr>`;
    }).join("");
}

// ── MODAL CREAR / EDITAR ──────────────────────────────────────────────────────
function mostrarModalNuevo() {
    document.getElementById("modal-titulo").textContent = "Nuevo Barbero";
    document.getElementById("f-id").value               = "";
    document.getElementById("f-nombre").value           = "";
    document.getElementById("f-alias").value            = "";
    document.getElementById("f-telefono").value         = "";
    document.getElementById("f-comision-tipo").value    = "porcentaje";
    document.getElementById("f-comision-valor").value   = "";
    document.getElementById("f-notas").value            = "";
    setError("error-modal", "");
    btnGuardar.disabled    = false;
    btnGuardar.textContent = "Guardar Barbero";
    modal.classList.add("active");
}

async function mostrarModalEditar(id) {
    setError("error-modal", "");
    try {
        const b = await window.api.apiRequest(`/api/barbers/${id}`);
        document.getElementById("modal-titulo").textContent     = "Editar Barbero";
        document.getElementById("f-id").value                   = b.id;
        document.getElementById("f-nombre").value               = b.full_name  || "";
        document.getElementById("f-alias").value                = b.alias      || "";
        document.getElementById("f-telefono").value             = b.phone      || "";
        document.getElementById("f-comision-tipo").value        = b.commission_type  || "porcentaje";
        document.getElementById("f-comision-valor").value       = b.commission_value ?? "";
        document.getElementById("f-notas").value                = b.notes      || "";
        btnGuardar.disabled    = false;
        btnGuardar.textContent = "Guardar Cambios";
        modal.classList.add("active");
    } catch (err) {
        setError("error-global", "No se pudo cargar el barbero: " + err.message);
    }
}

function cerrarModal() { modal.classList.remove("active"); }

async function guardarBarbero() {
    const id     = document.getElementById("f-id").value;
    const nombre = document.getElementById("f-nombre").value.trim();
    const alias  = document.getElementById("f-alias").value.trim()    || null;
    const phone  = document.getElementById("f-telefono").value.trim() || null;
    const cType  = document.getElementById("f-comision-tipo").value;
    const cVal   = parseFloat(document.getElementById("f-comision-valor").value) || 0;
    const notas  = document.getElementById("f-notas").value.trim()   || null;

    if (!nombre) { setError("error-modal", "El nombre es obligatorio."); return; }

    const body = { full_name: nombre, alias, phone, commission_type: cType, commission_value: cVal, notes: notas };

    btnGuardar.disabled    = true;
    btnGuardar.textContent = "Guardando...";
    setError("error-modal", "");

    try {
        if (id) {
            await window.api.apiRequest(`/api/barbers/${id}`, { method: "PATCH", body });
        } else {
            await window.api.apiRequest("/api/barbers", { method: "POST", body });
        }
        cerrarModal();
        await cargarBarberos();
    } catch (err) {
        setError("error-modal", err.message);
        btnGuardar.disabled    = false;
        btnGuardar.textContent = id ? "Guardar Cambios" : "Guardar Barbero";
    }
}

// ── DESACTIVAR ────────────────────────────────────────────────────────────────
async function desactivar(id, nombre) {
    if (!confirm(`¿Desactivar a ${nombre}? Seguirá en el historial pero no aparecerá en selects.`)) return;
    setError("error-global", "");
    try {
        await window.api.apiRequest(`/api/barbers/${id}/deactivate`, { method: "PATCH" });
        await cargarBarberos();
    } catch (err) {
        setError("error-global", err.message);
    }
}

// ── ELIMINAR (solo el dueño, Mateo) ────────────────────────────────────────────
async function eliminarBarbero(id, nombre) {
    const msg = `Esto ocultará "${nombre}" de todo el sistema para uso futuro. ` +
        `El historial de ventas ya registrado se conserva, pero se marcará como eliminado. ` +
        `Esta acción no se puede deshacer. ¿Continuar?`;
    if (!confirm(msg)) return;
    setError("error-global", "");
    try {
        await window.api.apiRequest(`/api/barbers/${id}`, { method: "DELETE" });
        await cargarBarberos();
    } catch (err) {
        const detail = err.responseData && err.responseData.detail;
        setError("error-global", (typeof detail === "string" ? detail : null) || err.message);
    }
}

// ── RENDIMIENTO ───────────────────────────────────────────────────────────────
async function verRendimiento(id) {
    const box = document.getElementById("modal-rendimiento");
    document.getElementById("rend-content").innerHTML = "Cargando...";
    box.classList.add("active");
    try {
        const r = await window.api.apiRequest(`/api/barbers/${id}/performance`);
        document.getElementById("rend-titulo").textContent = `Rendimiento — ${r.full_name}`;
        document.getElementById("rend-content").innerHTML = `
            <div class="rend-row"><span class="lbl">Período</span><span class="val">${r.period.start_date} → ${r.period.end_date}</span></div>
            <div class="rend-row"><span class="lbl">Comandas cerradas</span><span class="val">${r.orders_count}</span></div>
            <div class="rend-row"><span class="lbl">Ventas totales</span><span class="val">${money(r.sales_total)}</span></div>
            <div class="rend-row"><span class="lbl">Tipo comisión</span><span class="val">${escHtml(r.commission_type)} — ${r.commission_value}${r.commission_type === "porcentaje" ? "%" : " fijo"}</span></div>
            <div class="rend-row"><span class="lbl">Comisión estimada</span><span class="val" style="color:#c89b3c;">${money(r.estimated_commission)}</span></div>
        `;
    } catch (err) {
        document.getElementById("rend-content").innerHTML = `<span style="color:#ef9a9a;">${err.message}</span>`;
    }
}

function cerrarRendimiento() {
    document.getElementById("modal-rendimiento").classList.remove("active");
}

// ── UTILS ─────────────────────────────────────────────────────────────────────
function setText(id, val) { const e = document.getElementById(id); if (e) e.textContent = val; }
function setError(id, msg) { const e = document.getElementById(id); if (e) e.textContent = msg; }
function money(n) {
    if (n == null) return "—";
    return "$ " + Number(n).toLocaleString("es-CO", { minimumFractionDigits: 0 });
}
function escHtml(s) {
    return String(s).replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;");
}
function escAttr(s) {
    return String(s).replace(/'/g, "\\'");
}
