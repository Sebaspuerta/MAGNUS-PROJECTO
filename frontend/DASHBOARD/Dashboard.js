document.addEventListener("DOMContentLoaded", async () => {

    const user = window.api.getAuthUser();

    const nameEl       = document.getElementById("user-name");
    const avatarEl     = document.getElementById("user-avatar");
    const welcomeEl    = document.getElementById("welcome-name");
    const dateEl       = document.getElementById("current-date");

    const displayName = user.full_name || user.username || "Usuario";
    if (nameEl)    nameEl.textContent    = displayName;
    if (welcomeEl) welcomeEl.textContent = displayName;
    if (avatarEl)  avatarEl.textContent  = displayName.charAt(0).toUpperCase();

    if (dateEl) {
        const now = new Date();
        dateEl.textContent = now.toLocaleDateString("es-CO", {
            weekday: "long", year: "numeric", month: "long", day: "numeric"
        });
    }

    document.getElementById("btn-logout").addEventListener("click", () => {
        window.api.clearAuthToken();
        window.location.replace("/LOGIN/login.html");
    });

    await loadSummary();

});

async function loadSummary() {

    function fmt(n)   { return n != null ? Number(n).toLocaleString("es-CO") : "—"; }
    function money(n) { return n != null ? "$ " + Number(n).toLocaleString("es-CO", { minimumFractionDigits: 0 }) : "—"; }

    try {
        const d = await window.api.apiRequest("/api/dashboard/summary");

        const today = d.today             || {};
        const cash  = d.cash              || {};
        const inv   = d.inventory         || {};
        const ar    = d.accounts_receivable || {};
        const alerts = d.alerts           || {};

        setText("kpi-total",   money(today.received_total));
        setText("kpi-closed",  fmt(today.orders_closed));
        setText("kpi-open",    fmt(today.orders_open));
        setText("kpi-alerts",  fmt(alerts.unread));

        const cashStatusEl = document.getElementById("cash-status");
        if (cashStatusEl) {
            const open = cash.has_open_register;
            cashStatusEl.innerHTML = open
                ? '<span class="badge badge-green">Abierta</span>'
                : '<span class="badge badge-red">Cerrada</span>';
        }

        setText("cash-amount", money(cash.expected_amount));

        const lowEl = document.getElementById("inv-low");
        const outEl = document.getElementById("inv-out");
        if (lowEl) {
            const n = inv.low_stock || 0;
            lowEl.innerHTML = n > 0
                ? `<span class="badge badge-orange">${n}</span>`
                : `<span class="badge badge-green">0</span>`;
        }
        if (outEl) {
            const n = inv.out_of_stock || 0;
            outEl.innerHTML = n > 0
                ? `<span class="badge badge-red">${n}</span>`
                : `<span class="badge badge-green">0</span>`;
        }

        setText("ar-count",   fmt(ar.pending_count));
        setText("ar-balance", money(ar.pending_balance));

        setText("sum-closed", fmt(today.orders_closed));
        setText("sum-open",   fmt(today.orders_open));
        setText("sum-total",  money(today.received_total));

    } catch (err) {
        ["kpi-total","kpi-closed","kpi-open","kpi-alerts",
         "cash-amount","ar-count","ar-balance",
         "sum-closed","sum-open","sum-total"].forEach(id => {
            const el = document.getElementById(id);
            if (el) { el.textContent = "Error"; el.className = "error-text"; }
        });
        console.error("Error cargando dashboard:", err.message);
    }
}

function setText(id, value) {
    const el = document.getElementById(id);
    if (el) el.textContent = value;
}
