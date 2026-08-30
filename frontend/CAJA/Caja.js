let cajaActual = null;

document.addEventListener("DOMContentLoaded", async () => {
    await cargarCaja();
});

// ── CARGA INICIAL ──────────────────────────────────────────────────────────────

async function cargarCaja() {
    setError("error-caja", "");
    try {
        const registros = await window.api.apiRequest("/api/cash-registers");
        // Mismo criterio que el Dashboard (dashboard_service.get_dashboard_summary):
        // la caja abierta MÁS RECIENTE, no la primera que aparezca en la lista.
        // El backend ya no permite dos cajas abiertas a la vez, pero si algo
        // raro dejara más de una, las dos pantallas deben coincidir en cuál es.
        const abiertas = registros.filter(r => !r.is_closed);
        cajaActual = abiertas.length
            ? abiertas.reduce((latest, r) => (r.id > latest.id ? r : latest))
            : null;
        renderEstado();
        if (cajaActual) {
            await cargarMovimientos();
        }
    } catch (err) {
        setError("error-caja", err.message);
    }
}

async function cargarMovimientos() {
    if (!cajaActual) return;
    const msg  = document.getElementById("msg-movimientos");
    const tabla = document.getElementById("tabla-movimientos");

    msg.textContent = "Cargando movimientos...";
    msg.style.display = "block";
    tabla.style.display = "none";

    try {
        const movs = await window.api.apiRequest(
            `/api/cash-movements?cash_register_id=${cajaActual.id}`
        );
        renderMovimientos(movs);
    } catch (err) {
        msg.textContent = "Error al cargar movimientos: " + err.message;
    }
}

// ── RENDER ─────────────────────────────────────────────────────────────────────

function renderEstado() {
    const abierta = cajaActual && !cajaActual.is_closed;

    const statusEl = document.getElementById("status");
    statusEl.textContent = abierta ? "ABIERTA" : "CERRADA";
    statusEl.className   = "badge " + (abierta ? "open" : "closed");

    setText("ventas",  abierta ? money(cajaActual.opening_amount)  : "—");
    setText("egresos", abierta && cajaActual.expected_amount != null
        ? money(cajaActual.expected_amount) : "—");
    setText("balance", "—");

    document.getElementById("info-sin-caja").style.display = abierta ? "none"  : "block";
    document.getElementById("info-caja").style.display     = abierta ? "block" : "none";
    document.getElementById("btn-abrir").style.display     = abierta ? "none"  : "inline-block";
    document.getElementById("btn-cerrar").style.display    = abierta ? "block" : "none";

    if (abierta) {
        setText("caja-id",        "#" + cajaActual.id);
        setText("caja-opened-at", fmtFecha(cajaActual.opened_at));
        setText("caja-opening",   money(cajaActual.opening_amount));
        setText("caja-expected",  cajaActual.expected_amount != null
            ? money(cajaActual.expected_amount) : "—");
    }
}

function renderMovimientos(movs) {
    const msg   = document.getElementById("msg-movimientos");
    const tabla = document.getElementById("tabla-movimientos");
    const tbody = document.getElementById("log");

    if (!movs || movs.length === 0) {
        msg.textContent = "Sin movimientos registrados en esta caja.";
        msg.style.display = "block";
        tabla.style.display = "none";
        return;
    }

    msg.style.display = "none";
    tabla.style.display = "table";

    tbody.innerHTML = movs.map(m => `
        <tr>
            <td>${escHtml(m.movement_type)}</td>
            <td>${escHtml(m.description)}</td>
            <td>${money(m.amount)}</td>
            <td>${m.payment_method ? escHtml(m.payment_method) : "—"}</td>
        </tr>
    `).join("");
}

// ── MODAL ABRIR ────────────────────────────────────────────────────────────────

function mostrarModalAbrir() {
    document.getElementById("input-apertura").value    = "";
    document.getElementById("input-notas-abrir").value = "";
    setError("error-abrir", "");
    setDisabled("btn-confirm-abrir", false, "Confirmar");
    abrirModal("modal-abrir");
}

async function confirmarAbrir() {
    const amount = parseFloat(document.getElementById("input-apertura").value);
    const notes  = document.getElementById("input-notas-abrir").value.trim() || null;

    if (isNaN(amount) || amount < 0) {
        setError("error-abrir", "Ingresa un monto de apertura válido (0 o más).");
        return;
    }

    setDisabled("btn-confirm-abrir", true, "Abriendo...");
    setError("error-abrir", "");

    try {
        const result = await window.api.apiRequest("/api/cash-registers/open", {
            method: "POST",
            body: { opening_amount: amount, notes }
        });
        cajaActual = result;
        cerrarModal("modal-abrir");
        renderEstado();
        await cargarMovimientos();
    } catch (err) {
        setError("error-abrir", err.message);
        setDisabled("btn-confirm-abrir", false, "Confirmar");
    }
}

// ── MODAL CERRAR ───────────────────────────────────────────────────────────────

function mostrarModalCerrar() {
    document.getElementById("input-cierre").value      = "";
    document.getElementById("input-notas-cerrar").value = "";
    setError("error-cerrar", "");
    document.getElementById("arqueo-result").style.display  = "none";
    document.getElementById("btn-confirm-cerrar").style.display = "inline-block";
    document.getElementById("btn-modal-ok").style.display       = "none";
    abrirModal("modal-cerrar");
}

async function confirmarCerrar() {
    const amount = parseFloat(document.getElementById("input-cierre").value);
    const notes  = document.getElementById("input-notas-cerrar").value.trim() || null;

    if (isNaN(amount) || amount < 0) {
        setError("error-cerrar", "Ingresa el monto contado en caja.");
        return;
    }

    setDisabled("btn-confirm-cerrar", true, "Cerrando...");
    setError("error-cerrar", "");

    try {
        const result = await window.api.apiRequest(
            `/api/cash-registers/${cajaActual.id}/close`,
            { method: "PATCH", body: { closing_amount: amount, notes } }
        );

        const diff = result.difference ?? 0;

        setText("arq-esperado", money(result.expected_amount));
        setText("arq-contado",  money(result.closing_amount));

        const diffEl = document.getElementById("arq-diferencia");
        diffEl.textContent = money(diff);
        diffEl.style.color = diff < 0 ? "#ef9a9a" : diff > 0 ? "#81c784" : "var(--text)";

        setText("balance", money(diff));

        document.getElementById("arqueo-result").style.display      = "block";
        document.getElementById("btn-confirm-cerrar").style.display = "none";
        document.getElementById("btn-modal-ok").style.display       = "inline-block";

        cajaActual = result;
        renderEstado();

    } catch (err) {
        setError("error-cerrar", err.message);
        setDisabled("btn-confirm-cerrar", false, "Confirmar Cierre");
    }
}

// ── UTILS ──────────────────────────────────────────────────────────────────────

function abrirModal(id)  { document.getElementById(id).classList.add("visible"); }
function cerrarModal(id) { document.getElementById(id).classList.remove("visible"); }

function setText(id, value) {
    const el = document.getElementById(id);
    if (el) el.textContent = value;
}

function setError(id, msg) {
    const el = document.getElementById(id);
    if (el) el.textContent = msg;
}

function setDisabled(id, disabled, label) {
    const el = document.getElementById(id);
    if (!el) return;
    el.disabled     = disabled;
    el.textContent  = label;
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

function escHtml(str) {
    return String(str)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;");
}
