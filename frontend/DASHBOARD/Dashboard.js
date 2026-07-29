// ── MODO CLARO / OSCURO ──────────────────────────────────────────────────────

function _themeIcon() {
    const isLight = document.body.classList.contains("light-mode");
    const i = document.querySelector("#btn-theme i");
    if (i) { i.setAttribute("data-lucide", isLight ? "moon" : "sun"); lucide.createIcons(); }
}

document.addEventListener("DOMContentLoaded", async () => {

    // Aplica preferencia guardada si el script anti-flash del <body> no la capturó
    if (localStorage.getItem("magnusTheme") === "light" && !document.body.classList.contains("light-mode")) {
        document.body.classList.add("light-mode");
    }
    _themeIcon();

    document.getElementById("btn-theme").addEventListener("click", function () {
        const isLight = document.body.classList.toggle("light-mode");
        localStorage.setItem("magnusTheme", isLight ? "light" : "dark");
        _themeIcon();
    });

    const user = window.api.getAuthUser();

    const nameEl       = document.getElementById("user-name");
    const avatarEl     = document.getElementById("user-avatar");
    const welcomeEl    = document.getElementById("welcome-name");
    const dateEl       = document.getElementById("current-date");

    const displayName = user.full_name || user.username || "Usuario";
    if (nameEl)    nameEl.textContent    = displayName;
    if (welcomeEl) welcomeEl.textContent = displayName;
    if (avatarEl)  avatarEl.textContent  = displayName.charAt(0).toUpperCase();

    const roleEl = document.getElementById("user-role");
    if (roleEl) roleEl.textContent = user.role || "—";

    // Engranaje: solo visible para Administrador
    const gearBtn = document.getElementById("btn-admin-gear");
    if (gearBtn && user.role === "Administrador") {
        gearBtn.style.display = "";
        gearBtn.addEventListener("click", openAdminModal);
    }

    // Filtro de navegación por rol
    _filterNavByRole(user.role);
    _filterHomeCardsByRole(user.role);

    document.getElementById("btn-close-admin").addEventListener("click", closeAdminModal);
    document.getElementById("modal-admin").addEventListener("click", function (e) {
        if (e.target === this) closeAdminModal();
    });

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

    if (user.role === "Barbero") {
        await loadMyCutsToday();
    } else {
        await loadSummary();
    }

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

// ── NAVEGACIÓN POR ROL ───────────────────────────────────────────────────────

function _filterNavByRole(role) {
    const NAV_ROLE_MAP = {
        "Barbero": [
            "/DASHBOARD/Dashboard.html",
            "/COMANDAS/Comandas.html",
            "/CLIENTES/Clientes.html",
            "/SERVICIOS/Servicios.html",
            "/INVENTARIOS/Inventario.html",
        ]
    };

    const allowed = NAV_ROLE_MAP[role];
    if (!allowed) return; // Administrador y demás roles: ven todo

    document.querySelectorAll(".sidebar .nav").forEach(function (a) {
        if (!allowed.includes(a.getAttribute("href"))) {
            a.style.display = "none";
        }
    });

    // Ocultar etiquetas de sección que queden sin ítems visibles
    document.querySelectorAll(".sidebar .nlabel").forEach(function (label) {
        var sibling = label.nextElementSibling;
        var hasVisible = false;
        while (sibling && !sibling.classList.contains("nlabel") && !sibling.classList.contains("logout")) {
            if (sibling.classList.contains("nav") && sibling.style.display !== "none") {
                hasVisible = true;
                break;
            }
            sibling = sibling.nextElementSibling;
        }
        if (!hasVisible) label.style.display = "none";
    });
}

// ── TARJETAS DE INICIO POR ROL ────────────────────────────────────────────────
// Un Barbero es un trabajador normal: solo ve su propio conteo de cortes del
// día, nunca dinero, caja ni fiados. Estas tarjetas ni siquiera intentan
// cargarse para ese rol (ver loadMyCutsToday / DOMContentLoaded).
function _filterHomeCardsByRole(role) {
    if (role !== "Barbero") return;

    const hideIds = [
        "kpi-card-total", "kpi-card-closed", "kpi-card-open", "kpi-card-alerts",
        "panel-caja", "panel-inventario", "panel-ar", "panel-resumen"
    ];
    hideIds.forEach(function (id) {
        const el = document.getElementById(id);
        if (el) el.style.display = "none";
    });

    ["grid-fila1", "grid-fila2"].forEach(function (id) {
        const grid = document.getElementById(id);
        if (grid) grid.style.display = "none";
    });

    const cortesCard = document.getElementById("kpi-card-cortes");
    if (cortesCard) cortesCard.style.display = "";
}

async function loadMyCutsToday() {
    try {
        const d = await window.api.apiRequest("/api/dashboard/mis-cortes-hoy");
        setText("kpi-cortes-hoy", d.cortes_hoy != null ? d.cortes_hoy : "—");
    } catch (err) {
        setText("kpi-cortes-hoy", "Error");
        console.error("Error cargando mis cortes de hoy:", err.message);
    }
}

// ── GESTIÓN DE ADMINISTRADOR ─────────────────────────────────────────────────

let _adminBarbers  = [];
let _activeSubForm = null; // { barberId, type: 'create' | 'reset' }

function openAdminModal() {
    document.getElementById("modal-admin").style.display = "flex";
    _activeSubForm = null;
    loadAdminBarbers();
    initMasterCodeForm();
}

function closeAdminModal() {
    document.getElementById("modal-admin").style.display = "none";
    _activeSubForm = null;
    _mcFormBound   = false;
}

async function loadAdminBarbers() {
    const list = document.getElementById("admin-barber-list");
    list.innerHTML = '<div class="adm-loading">Cargando barberos...</div>';
    try {
        _adminBarbers = await window.api.apiRequest("/api/barbers?include_inactive=true");
        renderAdminBarbers();
    } catch (err) {
        const detail = (err.responseData && err.responseData.detail) || err.message;
        list.innerHTML = `<div class="adm-error">${typeof detail === "string" ? detail : "Error al cargar."}</div>`;
    }
}

function renderAdminBarbers() {
    const list = document.getElementById("admin-barber-list");
    if (!_adminBarbers.length) {
        list.innerHTML = '<div class="adm-empty">No hay barberos registrados.</div>';
        return;
    }
    list.innerHTML = _adminBarbers.map(renderBarberRow).join("");
    lucide.createIcons();
}

function renderBarberRow(b) {
    const dot = b.has_user
        ? `<span class="ab-dot ${b.user_is_active ? "ab-active" : "ab-inactive"}"></span>`
        : "";

    const userBadge = b.has_user
        ? `<span class="ab-username">@${b.user_username}</span>`
        : `<span class="ab-no-user">Sin usuario</span>`;

    const actions = b.has_user
        ? `<button class="ab-btn ab-btn-secondary" onclick="showSubForm(${b.id},'reset')">
               <i data-lucide="key"></i> Cambiar contrase&ntilde;a
           </button>
           <button class="ab-toggle ${b.user_is_active ? "active" : "inactive"}"
                   onclick="toggleBarberAccess(${b.id})"
                   title="${b.user_is_active ? "Desactivar acceso" : "Activar acceso"}">
               <i data-lucide="${b.user_is_active ? "toggle-right" : "toggle-left"}"></i>
               ${b.user_is_active ? "Activo" : "Inactivo"}
           </button>`
        : `<button class="ab-btn ab-btn-primary" onclick="showSubForm(${b.id},'create')">
               <i data-lucide="user-plus"></i> Crear usuario
           </button>`;

    const subForm = (_activeSubForm && _activeSubForm.barberId === b.id)
        ? `<div class="ab-subform">${renderSubForm(b.id, _activeSubForm.type)}</div>`
        : "";

    return `
        <div class="ab-row" id="ab-row-${b.id}">
            <div class="ab-info">
                ${dot}
                <span class="ab-name">${b.full_name}</span>
                ${userBadge}
            </div>
            <div class="ab-actions">${actions}</div>
            ${subForm}
            <div class="ab-msg" id="ab-msg-${b.id}"></div>
        </div>`;
}

function renderSubForm(barberId, type) {
    const isCreate = type === "create";
    return `
        <form class="ab-pw-form" onsubmit="submitPasswordForm(event,${barberId},'${type}')">
            <p class="ab-pw-hint">
                M&iacute;nimo 8 caracteres, al menos una letra y un n&uacute;mero.
            </p>
            <div class="ab-pw-fields">
                <input type="password" id="ab-pw-${barberId}"
                       placeholder="${isCreate ? "Nueva contrase&ntilde;a" : "Nueva contrase&ntilde;a"}"
                       autocomplete="new-password" required>
                <input type="password" id="ab-pw2-${barberId}"
                       placeholder="Confirmar contrase&ntilde;a"
                       autocomplete="new-password" required>
            </div>
            <div id="ab-form-msg-${barberId}" class="ab-form-msg"></div>
            <div class="ab-pw-btns">
                <button type="submit" class="ab-btn ab-btn-primary">
                    <i data-lucide="${isCreate ? "user-plus" : "key"}"></i>
                    ${isCreate ? "Crear" : "Actualizar"}
                </button>
                <button type="button" class="ab-btn ab-btn-cancel"
                        onclick="cancelSubForm(${barberId})">Cancelar</button>
            </div>
        </form>`;
}

function showSubForm(barberId, type) {
    _activeSubForm = { barberId, type };
    renderAdminBarbers();
    setTimeout(() => {
        const el = document.getElementById(`ab-pw-${barberId}`);
        if (el) el.focus();
    }, 40);
}

function cancelSubForm(barberId) {
    _activeSubForm = null;
    renderAdminBarbers();
}

async function submitPasswordForm(event, barberId, type) {
    event.preventDefault();
    const pw1   = document.getElementById(`ab-pw-${barberId}`).value;
    const pw2   = document.getElementById(`ab-pw2-${barberId}`).value;
    const msgEl = document.getElementById(`ab-form-msg-${barberId}`);

    if (pw1 !== pw2) {
        msgEl.textContent = "Las contraseñas no coinciden.";
        msgEl.className = "ab-form-msg ab-form-msg-error";
        return;
    }

    msgEl.textContent = "Procesando...";
    msgEl.className = "ab-form-msg";

    const url    = type === "create"
        ? `/api/barbers/${barberId}/create-user`
        : `/api/barbers/${barberId}/reset-password`;
    const method = type === "create" ? "POST" : "PUT";

    try {
        const result = await window.api.apiRequest(url, { method, body: { password: pw1 } });
        const ok = type === "create"
            ? `Usuario creado: @${result.username}`
            : (result.detail || "Contraseña actualizada.");

        _activeSubForm = null;
        await loadAdminBarbers();

        const rowMsg = document.getElementById(`ab-msg-${barberId}`);
        if (rowMsg) {
            rowMsg.textContent = ok;
            rowMsg.className = "ab-msg ab-msg-success";
            setTimeout(() => { const el = document.getElementById(`ab-msg-${barberId}`); if (el) el.textContent = ""; }, 4500);
        }
    } catch (err) {
        const detail = (err.responseData && err.responseData.detail) || err.message;
        if (msgEl) {
            msgEl.textContent = typeof detail === "string" ? detail : "Error al procesar.";
            msgEl.className = "ab-form-msg ab-form-msg-error";
        }
    }
}

// ── CÓDIGO MAESTRO DE RECUPERACIÓN ──────────────────────────────

let _mcFormBound = false;

function initMasterCodeForm() {
    const btn   = document.getElementById("btn-save-mc");
    const msgEl = document.getElementById("mc-msg");
    if (!btn || _mcFormBound) return;
    _mcFormBound = true;

    document.getElementById("mc-current-pw").value = "";
    document.getElementById("mc-new-code").value = "";
    if (msgEl) { msgEl.textContent = ""; msgEl.className = "ab-form-msg"; }

    btn.addEventListener("click", async function () {
        const currentPw = document.getElementById("mc-current-pw").value;
        const newCode   = document.getElementById("mc-new-code").value;

        if (!currentPw || !newCode) {
            msgEl.textContent = "Completa ambos campos.";
            msgEl.className   = "ab-form-msg ab-form-msg-error";
            return;
        }

        btn.disabled      = true;
        msgEl.textContent = "Guardando...";
        msgEl.className   = "ab-form-msg";

        try {
            const result = await window.api.apiRequest("/api/security/master-code", {
                method: "POST",
                body: { current_password: currentPw, master_code: newCode }
            });
            msgEl.textContent = result.detail || "Código maestro actualizado.";
            msgEl.className   = "ab-form-msg ab-form-msg-success";
            document.getElementById("mc-current-pw").value = "";
            document.getElementById("mc-new-code").value   = "";
        } catch (err) {
            const detail = (err.responseData && err.responseData.detail) || err.message;
            msgEl.textContent = typeof detail === "string" ? detail : "Error al guardar.";
            msgEl.className   = "ab-form-msg ab-form-msg-error";
        } finally {
            btn.disabled = false;
        }
    });
}

async function toggleBarberAccess(barberId) {
    try {
        const result = await window.api.apiRequest(
            `/api/barbers/${barberId}/toggle-access`, { method: "PUT" }
        );
        await loadAdminBarbers();
        const msgEl = document.getElementById(`ab-msg-${barberId}`);
        if (msgEl) {
            msgEl.textContent = result.user_is_active ? "Acceso activado." : "Acceso desactivado.";
            msgEl.className   = `ab-msg ${result.user_is_active ? "ab-msg-success" : "ab-msg-warn"}`;
            setTimeout(() => { const el = document.getElementById(`ab-msg-${barberId}`); if (el) el.textContent = ""; }, 3500);
        }
    } catch (err) {
        const detail = (err.responseData && err.responseData.detail) || err.message;
        const msgEl  = document.getElementById(`ab-msg-${barberId}`);
        if (msgEl) {
            msgEl.textContent = typeof detail === "string" ? detail : "Error.";
            msgEl.className   = "ab-msg ab-msg-error";
        }
    }
}
