let cuentas  = [];
let clientes = [];

// ── INIT ───────────────────────────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => recargar());

async function recargar() {
    setError("error-global", "");
    await Promise.all([cargarResumen(), cargarClientes()]);
    await cargarCuentas();
}

// ── RESUMEN ───────────────────────────────────────────────────────────────────
async function cargarResumen() {
    try {
        const s = await window.api.apiRequest("/api/accounts-receivable/summary");
        setText("kpi-pending-count",   s.pending_count   ?? "—");
        setText("kpi-pending-balance", s.pending_balance != null ? money(s.pending_balance) : "—");
        setText("kpi-overdue-count",   s.overdue_count   ?? "—");
        setText("kpi-overdue-balance", s.overdue_balance != null ? money(s.overdue_balance) : "—");
    } catch (err) {
        // resumen no crítico: si falla, deja "—"
        console.warn("Resumen no disponible:", err.message);
    }
}

// ── CATÁLOGO CLIENTES ─────────────────────────────────────────────────────────
async function cargarClientes() {
    try {
        const lista = await window.api.apiRequest("/api/clients");
        clientes = lista.filter(c => c.is_active);
    } catch (err) {
        clientes = [];
    }
}

// ── CUENTAS ───────────────────────────────────────────────────────────────────
async function cargarCuentas() {
    const msg = document.getElementById("msg-carga");
    if (msg) { msg.textContent = "Cargando cuentas..."; msg.style.display = "block"; }

    try {
        cuentas = await window.api.apiRequest("/api/accounts-receivable");
        if (msg) msg.style.display = "none";
        renderGrid(cuentas);
        renderHistorial(cuentas);
    } catch (err) {
        if (msg) msg.textContent = "Error al cargar: " + err.message;
        setError("error-global", err.message);
    }
}

// ── RENDER GRID ────────────────────────────────────────────────────────────────
function renderGrid(lista) {
    const grid = document.getElementById("grid");

    if (!lista.length) {
        grid.innerHTML = '<div style="color:var(--muted);padding:8px 0;">No hay cuentas por cobrar. Las comandas cerradas como Fiado aparecerán aquí.</div>';
        return;
    }

    const activas = lista.filter(c => c.is_active);

    if (!activas.length) {
        grid.innerHTML = '<div style="color:var(--muted);padding:8px 0;">Todas las cuentas están saldadas.</div>';
        return;
    }

    grid.innerHTML = activas.map(c => {
        const nombreCliente = nombreDe(c.client_id);
        const { badgeClass, badgeLabel } = estadoBadge(c);

        const vencidoAlert = esVencido(c)
            ? `<div class="alert">⚠ Vencida desde ${c.due_date}</div>`
            : "";

        const progreso = c.total_amount > 0
            ? Math.min(100, Math.round((c.paid_amount / c.total_amount) * 100))
            : 0;

        return `<div class="card">
            <div class="title">${escHtml(nombreCliente)}</div>
            ${c.notes ? `<div class="meta">${escHtml(c.notes)}</div>` : ""}
            <div class="meta">Total: <strong style="color:var(--text);">${money(c.total_amount)}</strong></div>
            <div class="meta">Pagado: ${money(c.paid_amount)}</div>
            <div class="meta">Saldo: <strong style="color:${c.balance > 0 ? 'var(--orange)' : 'var(--green)'};">${money(c.balance)}</strong></div>
            ${c.due_date ? `<div class="meta">Vence: ${c.due_date}</div>` : ""}

            <div style="margin:10px 0;height:4px;background:rgba(255,255,255,.1);border-radius:4px;">
                <div style="height:100%;width:${progreso}%;background:var(--green);border-radius:4px;transition:.3s;"></div>
            </div>

            <span class="badge ${badgeClass}">${badgeLabel}</span>
            ${vencidoAlert}

            ${c.balance > 0 ? `
            <div style="margin-top:12px;">
                <button class="btn primary" style="width:100%;" onclick="mostrarModalAbono(${c.id}, ${c.balance}, '${escAttr(nombreCliente)}')">
                    Registrar Abono
                </button>
            </div>` : ""}
        </div>`;
    }).join("");
}

// ── HISTORIAL DE ABONOS ───────────────────────────────────────────────────────
function renderHistorial(lista) {
    const msg   = document.getElementById("msg-abonos");
    const tabla = document.getElementById("tabla-abonos");
    const tbody = document.getElementById("history");

    const todosAbonos = [];
    lista.forEach(c => {
        const nombre = nombreDe(c.client_id);
        (c.payments || []).forEach(p => {
            todosAbonos.push({ ...p, clienteNombre: nombre });
        });
    });

    todosAbonos.sort((a, b) => new Date(b.payment_date) - new Date(a.payment_date));

    if (!todosAbonos.length) {
        msg.textContent   = "Aún no hay abonos registrados.";
        msg.style.display = "block";
        tabla.style.display = "none";
        return;
    }

    msg.style.display   = "none";
    tabla.style.display = "table";

    tbody.innerHTML = todosAbonos.map(p => `
        <tr>
            <td>${escHtml(p.clienteNombre)}</td>
            <td style="color:var(--green);font-weight:600;">${money(p.amount)}</td>
            <td>${p.payment_method ? escHtml(p.payment_method) : "—"}</td>
            <td style="font-size:.8rem;">${p.note ? escHtml(p.note) : "—"}</td>
            <td style="font-size:.78rem;color:var(--muted);">${fmtFecha(p.payment_date)}</td>
        </tr>
    `).join("");
}

// ── MODAL ABONO ───────────────────────────────────────────────────────────────
function mostrarModalAbono(id, balance, nombreCliente) {
    document.getElementById("abono-id").value     = id;
    document.getElementById("abono-amount").value = "";
    document.getElementById("abono-method").value = "";
    document.getElementById("abono-note").value   = "";
    setError("error-abono", "");
    setDisabled("btn-confirmar-abono", false, "Confirmar Abono");

    const info = document.getElementById("abono-info");
    if (info) info.textContent = `Cliente: ${nombreCliente} | Saldo pendiente: ${money(balance)}`;

    document.getElementById("modal-abono").classList.add("active");
}

function cerrarModal() {
    document.getElementById("modal-abono").classList.remove("active");
}

async function confirmarAbono() {
    const id     = document.getElementById("abono-id").value;
    const monto  = parseFloat(document.getElementById("abono-amount").value);
    const metodo = document.getElementById("abono-method").value || null;
    const nota   = document.getElementById("abono-note").value.trim() || null;

    if (isNaN(monto) || monto <= 0) {
        setError("error-abono", "Ingresa un monto mayor a 0.");
        return;
    }

    setDisabled("btn-confirmar-abono", true, "Registrando...");
    setError("error-abono", "");

    try {
        await window.api.apiRequest(`/api/accounts-receivable/${id}/payments`, {
            method: "POST",
            body:   { amount: monto, payment_method: metodo, note: nota }
        });
        cerrarModal();
        await recargar();
    } catch (err) {
        setError("error-abono", err.message);
        setDisabled("btn-confirmar-abono", false, "Confirmar Abono");
    }
}

// ── HELPERS ────────────────────────────────────────────────────────────────────
function estadoBadge(c) {
    if (esVencido(c))        return { badgeClass: "late",    badgeLabel: "VENCIDA"  };
    const s = c.status?.toLowerCase();
    if (s === "pagada")      return { badgeClass: "paid",    badgeLabel: "PAGADA"   };
    if (s === "parcial")     return { badgeClass: "partial", badgeLabel: "PARCIAL"  };
    return                          { badgeClass: "pending", badgeLabel: "PENDIENTE"};
}

function esVencido(c) {
    if (!c.due_date || c.balance <= 0) return false;
    return new Date(c.due_date) < new Date();
}

function nombreDe(clientId) {
    if (!clientId) return "Sin cliente";
    const c = clientes.find(cl => cl.id === clientId);
    return c ? c.full_name : `Cliente #${clientId}`;
}

// ── UTILS ─────────────────────────────────────────────────────────────────────
function setText(id, v)  { const e = document.getElementById(id); if (e) e.textContent = v; }
function setError(id, m) { const e = document.getElementById(id); if (e) e.textContent = m; }
function setDisabled(id, disabled, label) {
    const e = document.getElementById(id);
    if (!e) return;
    e.disabled    = disabled;
    e.textContent = label;
}
function money(n) {
    if (n == null) return "—";
    return "$ " + Number(n).toLocaleString("es-CO", { minimumFractionDigits: 0 });
}
function fmtFecha(iso) {
    if (!iso) return "—";
    return new Date(iso).toLocaleString("es-CO", {
        year: "numeric", month: "short", day: "numeric",
        hour: "2-digit", minute: "2-digit"
    });
}
function escHtml(s)  { return String(s).replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;"); }
function escAttr(s)  { return String(s).replace(/'/g,"\\'"); }
