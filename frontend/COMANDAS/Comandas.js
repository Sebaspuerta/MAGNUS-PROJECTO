// ── ESTADO GLOBAL ──────────────────────────────────────────────────────────────
let catalogos = {
    clientes:    [],
    barberos:    [],
    servicios:   [],
    productos:   [],
    cajaAbierta: null
};
let comandaActual = null;

// ── INIT ───────────────────────────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
    cargarCatalogos();
    cargarLista();
});

// ── CATÁLOGOS ─────────────────────────────────────────────────────────────────
async function cargarCatalogos() {
    try {
        const resultados = await Promise.allSettled([
            window.api.apiRequest("/api/clients"),
            window.api.apiRequest("/api/barbers/active-basic"),
            window.api.apiRequest("/api/services"),
            window.api.apiRequest("/api/inventory/products"),
            window.api.apiRequest("/api/cash-registers"),
        ]);
        const val = i => resultados[i].status === "fulfilled" ? (resultados[i].value || []) : [];
        const clientes  = val(0);
        const barberos  = val(1);
        const servicios = val(2);
        const productos = val(3);
        const cajas     = val(4);
        catalogos.clientes    = clientes.filter(c => c.is_active);
        catalogos.barberos    = barberos; // /active-basic ya solo devuelve barberos activos
        catalogos.servicios   = servicios.filter(s => s.is_active);
        catalogos.productos   = productos.filter(p => p.is_active);
        catalogos.cajaAbierta = cajas.find(c => !c.is_closed) || null;

        poblarSelect("nueva-barbero",  catalogos.barberos,  "Sin asignar",    b => ({ v: b.id, t: b.full_name }));
        poblarSelect("cobrar-barbero", catalogos.barberos,  "— seleccionar —",b => ({ v: b.id, t: b.full_name }));
        actualizarSelectItem();
    } catch (err) {
        console.error("Error cargando catálogos:", err.message);
    }
}

function poblarSelect(id, items, defaultLabel, mapFn) {
    const sel = document.getElementById(id);
    if (!sel) return;
    sel.innerHTML = `<option value="">${escHtml(defaultLabel)}</option>` +
        items.map(i => {
            const { v, t } = mapFn(i);
            return `<option value="${v}">${escHtml(t)}</option>`;
        }).join("");
}

function actualizarSelectItem() {
    const tipo     = document.getElementById("item-tipo")?.value || "servicio";
    const lista    = tipo === "servicio" ? catalogos.servicios : catalogos.productos;
    const priceKey = tipo === "servicio" ? "price" : "sale_price";

    const sel = document.getElementById("item-select");
    if (!sel) return;
    sel.innerHTML = '<option value="">— elegir —</option>' +
        lista.map(i =>
            `<option value="${i.id}" data-price="${i[priceKey]}">${escHtml(i.name)} — ${money(i[priceKey])}</option>`
        ).join("");

    if (document.getElementById("item-precio")) {
        document.getElementById("item-precio").value = "";
    }
}

function autoFillPrecio() {
    const sel = document.getElementById("item-select");
    const opt = sel?.selectedOptions[0];
    if (opt?.dataset.price) {
        document.getElementById("item-precio").value = opt.dataset.price;
    }
}

// ── LISTA DE COMANDAS ─────────────────────────────────────────────────────────
async function cargarLista() {
    const msg   = document.getElementById("msg-lista");
    const tabla = document.getElementById("tabla-lista");
    if (msg)   { msg.textContent = "Cargando comandas..."; msg.style.display = "block"; }
    if (tabla) { tabla.style.display = "none"; }

    try {
        const ordenes = await window.api.apiRequest("/api/orders");
        renderLista(ordenes);
    } catch (err) {
        if (msg) msg.textContent = "Error al cargar: " + err.message;
    }
}

function renderLista(ordenes) {
    const msg   = document.getElementById("msg-lista");
    const tabla = document.getElementById("tabla-lista");
    const tbody = document.getElementById("body-lista");

    if (!ordenes || ordenes.length === 0) {
        if (msg)   { msg.textContent = "No hay comandas aún. Crea la primera con + Nueva Comanda."; msg.style.display = "block"; }
        if (tabla) { tabla.style.display = "none"; }
        return;
    }

    if (msg)   { msg.style.display = "none"; }
    if (tabla) { tabla.style.display = "table"; }

    ordenes.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));

    tbody.innerHTML = ordenes.map(o => {
        const cliente = o.client_id
            ? (catalogos.clientes.find(c => c.id === o.client_id)?.full_name || `Cliente #${o.client_id}`)
            : "—";
        const barbero = o.barber_id
            ? (o.barber_name || catalogos.barberos.find(b => b.id === o.barber_id)?.full_name || `Barbero #${o.barber_id}`)
            : "—";

        const { clase, label } = statusBadge(o.status);
        const fiadoCell = o.is_fiado
            ? '<span class="badge" style="background:#1565c0;font-size:.7rem;">Sí</span>'
            : "—";
        const btnEstilo = o.status === "abierta"
            ? 'class="btn primary" style="padding:5px 12px;font-size:.78rem;"'
            : 'class="btn secondary" style="padding:5px 12px;font-size:.78rem;"';

        return `<tr>
            <td style="color:var(--gold);font-weight:600;">#${o.id}</td>
            <td>${escHtml(cliente)}</td>
            <td>${escHtml(barbero)}</td>
            <td><span class="badge ${clase}" style="font-size:.7rem;">${label}</span></td>
            <td style="color:var(--text);">${money(o.total)}</td>
            <td>${fiadoCell}</td>
            <td>${fmtFecha(o.created_at)}</td>
            <td><button ${btnEstilo} onclick="abrirDetalle(${o.id})">Ver</button></td>
        </tr>`;
    }).join("");
}

// ── DETALLE ───────────────────────────────────────────────────────────────────
async function abrirDetalle(id) {
    setError("error-detalle", "");
    try {
        const o = await window.api.apiRequest(`/api/orders/${id}`);
        comandaActual = o;
        renderDetalle();
        mostrarVista("detalle");
    } catch (err) {
        alert("Error al abrir comanda: " + err.message);
    }
}

function renderDetalle() {
    const o = comandaActual;
    if (!o) return;

    setText("det-id",        o.id);
    setText("det-fecha",     fmtFecha(o.created_at));
    setText("det-subtotal",  fmt(o.subtotal));
    setText("det-descuento", fmt(o.discount));
    setText("det-total",     fmt(o.total));
    setText("det-pagado",    fmt(o.amount_paid));

    const clienteNombre = o.client_id
        ? (catalogos.clientes.find(c => c.id === o.client_id)?.full_name || `Cliente #${o.client_id}`)
        : "Sin cliente";
    const barberoNombre = o.barber_id
        ? (o.barber_name || catalogos.barberos.find(b => b.id === o.barber_id)?.full_name || `Barbero #${o.barber_id}`)
        : "Sin asignar";
    setText("det-cliente", clienteNombre);
    setText("det-barbero", barberoNombre);

    const fiadoBadge = document.getElementById("det-fiado-badge");
    if (fiadoBadge) fiadoBadge.style.display = o.is_fiado ? "inline-block" : "none";

    const { clase, label } = payStatusBadge(o.payment_status, o.is_fiado);
    const statusEl = document.getElementById("det-status-pago");
    if (statusEl) { statusEl.className = `badge ${clase}`; statusEl.textContent = label; }

    renderItems(o.items);

    const abierta     = o.status === "abierta";
    const accionesEl  = document.getElementById("det-acciones");
    const cerrarEl    = document.getElementById("panel-cerrar");
    if (accionesEl) accionesEl.style.display = abierta ? "flex" : "none";
    if (cerrarEl)   cerrarEl.style.display   = abierta ? "block" : "none";

    setError("error-detalle", "");
}

function renderItems(items) {
    const container = document.getElementById("det-items");
    if (!container) return;

    if (!items || items.length === 0) {
        container.innerHTML = '<div style="color:var(--muted);font-size:.82rem;padding:8px 0;">Sin ítems. Agrega servicios o productos.</div>';
        return;
    }

    const abierta = comandaActual?.status === "abierta";

    container.innerHTML = items.map(it => {
        const nombre = it.display_name ||
            (it.item_type === "servicio"
                ? (catalogos.servicios.find(s => s.id === it.service_id)?.name || it.description || `Servicio #${it.service_id}`)
                : (catalogos.productos.find(p => p.id === it.product_id)?.name || it.description || `Producto #${it.product_id}`));

        const badge  = `<small style="color:var(--muted);font-size:.68rem;background:rgba(255,255,255,.06);padding:1px 6px;border-radius:4px;">${it.item_type}</small>`;
        const borrar = abierta
            ? `<button onclick="eliminarItem(${it.id})" class="btn danger" style="padding:4px 10px;font-size:.78rem;min-width:32px;">✕</button>`
            : "";

        return `<div class="item">
            <div>
                <strong>${escHtml(nombre)}</strong> ${badge}<br>
                <small>${money(it.unit_price)} × ${it.quantity} = ${money(it.total_price)}</small>
            </div>
            <div>${borrar}</div>
        </div>`;
    }).join("");
}

// ── MODAL NUEVA COMANDA ───────────────────────────────────────────────────────
async function mostrarModalNueva() {
    const el      = id => document.getElementById(id);
    const btnNueva = document.getElementById("btn-nueva");

    if (btnNueva) { btnNueva.disabled = true; btnNueva.textContent = "Cargando..."; }
    await cargarCatalogos();
    if (btnNueva) { btnNueva.disabled = false; btnNueva.textContent = "+ Nueva Comanda"; }

    el("nueva-cliente-id").value = "";
    el("nueva-cliente-buscar").value = "";
    ocultarResultadosClienteNueva();

    let user = window.api.getAuthUser();
    if (user.role === "Barbero" && !user.barber_id) {
        // Sesiones iniciadas antes de que el login empezara a guardar barber_id:
        // se refresca una vez desde /me para no forzar un nuevo login.
        try {
            const me = await window.api.apiRequest("/api/security/me");
            window.api.setAuthUser({ username: me.username, full_name: me.full_name, role: me.role, id: me.id, barber_id: me.barber_id });
            user = window.api.getAuthUser();
        } catch (e) { /* si falla, el campo simplemente arranca vacío */ }
    }
    const propioBarberoId = user.role === "Barbero" && user.barber_id ? String(user.barber_id) : "";
    el("nueva-barbero").value = propioBarberoId;

    el("nueva-fiado").checked  = false;
    el("nueva-notas").value    = "";
    setError("error-nueva", "");
    setDisabled("btn-confirm-nueva", false, "Crear Comanda");
    abrirModal("modal-nueva");
}

async function confirmarNueva() {
    const clienteId = parseInt(document.getElementById("nueva-cliente-id").value) || null;
    const barberoId = parseInt(document.getElementById("nueva-barbero").value) || null;
    const esFiado   = document.getElementById("nueva-fiado").checked;
    const notas     = document.getElementById("nueva-notas").value.trim() || null;

    setDisabled("btn-confirm-nueva", true, "Creando...");
    setError("error-nueva", "");

    try {
        const o = await window.api.apiRequest("/api/orders", {
            method: "POST",
            body: { client_id: clienteId, barber_id: barberoId, is_fiado: esFiado, notes: notas, discount: 0 }
        });
        cerrarModal("modal-nueva");
        comandaActual = o;
        renderDetalle();
        mostrarVista("detalle");
        cargarLista();
    } catch (err) {
        setError("error-nueva", err.message);
        setDisabled("btn-confirm-nueva", false, "Crear Comanda");
    }
}

// ── REGISTRO RÁPIDO (corte o producto suelto, sin abrir comanda manualmente) ──
let rapidoTipoActual = null; // "corte" | "producto"

async function mostrarModalRapido() {
    const btn = document.getElementById("btn-rapido");
    if (btn) { btn.disabled = true; }
    await cargarCatalogos();
    if (btn) { btn.disabled = false; }

    rapidoTipoActual = null;
    document.getElementById("rapido-paso-elegir").style.display = "block";
    document.getElementById("rapido-paso-form").style.display = "none";
    setError("error-rapido", "");
    abrirModal("modal-rapido");
}

function elegirTipoRapido(tipo) {
    rapidoTipoActual = tipo;
    setError("error-rapido", "");
    setText("rapido-preview", "");

    const esCorte = tipo === "corte";
    setText("rapido-form-titulo", esCorte ? "Registrar corte" : "Registrar producto");
    setText("rapido-barbero-label", esCorte ? "Barbero (quién hizo el corte)" : "Barbero / vendedor");

    poblarSelect("rapido-barbero", catalogos.barberos, "— seleccionar —", b => ({ v: b.id, t: b.full_name }));
    poblarSelect("rapido-servicio", catalogos.servicios, "— seleccionar —", s => ({ v: s.id, t: `${s.name} — ${money(s.price)}` }));

    document.getElementById("rapido-producto-id").value = "";
    document.getElementById("rapido-producto-buscar").value = "";
    ocultarResultadosProductoRapido();

    document.getElementById("rapido-campo-servicio").style.display = esCorte ? "block" : "none";
    document.getElementById("rapido-campo-producto").style.display = esCorte ? "none" : "block";
    document.getElementById("rapido-cantidad").value = "1";
    document.getElementById("rapido-metodo").value = "efectivo";
    document.getElementById("rapido-monto").value = "";
    document.getElementById("rapido-nota").value = "";

    document.getElementById("rapido-paso-elegir").style.display = "none";
    document.getElementById("rapido-paso-form").style.display = "block";
    setDisabled("btn-confirm-rapido", false, "Registrar");
    autoFillPrecioRapido();
}

function volverPasoElegirRapido() {
    rapidoTipoActual = null;
    document.getElementById("rapido-paso-elegir").style.display = "block";
    document.getElementById("rapido-paso-form").style.display = "none";
}

function autoFillPrecioRapido() {
    if (!rapidoTipoActual) return;

    if (rapidoTipoActual === "corte") {
        const sel = document.getElementById("rapido-servicio");
        const svc = catalogos.servicios.find(s => s.id === parseInt(sel.value));
        setText("rapido-preview", svc ? `Total a cobrar: ${money(svc.price)}` : "");
    } else {
        const cant = parseInt(document.getElementById("rapido-cantidad").value) || 1;
        const prodId = parseInt(document.getElementById("rapido-producto-id").value);
        const prod = catalogos.productos.find(p => p.id === prodId);
        setText("rapido-preview", prod ? `Total a cobrar: ${money(prod.sale_price * cant)}` : "");
    }
}

// ── PICKER DE PRODUCTO CON THUMBNAIL (registro rápido) ────────────────────────
const RAPIDO_PLACEHOLDER_SVG =
    '<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2">' +
    '<path d="M21 8l-9-5-9 5 9 5 9-5z"/><path d="M3 8v8l9 5 9-5V8"/><path d="M12 13v8"/></svg>';

function filtrarProductosRapido() {
    const q = document.getElementById("rapido-producto-buscar").value.trim().toLowerCase();
    const contenedor = document.getElementById("rapido-producto-resultados");

    const productoActualId = parseInt(document.getElementById("rapido-producto-id").value);
    // Si el texto coincide exactamente con el producto ya elegido, no re-filtramos
    // (evita que reabrir el foco vuelva a mostrar la lista completa sin sentido).
    const coincidencias = catalogos.productos
        .filter(p => p.name.toLowerCase().includes(q))
        .slice(0, 30);

    if (!coincidencias.length) {
        contenedor.innerHTML = '<div class="rapido-producto-vacio">Sin productos que coincidan.</div>';
    } else {
        contenedor.innerHTML = coincidencias.map(p => {
            const thumb = p.photo_url
                ? `<img class="rapido-producto-thumb" src="${escAttr(p.photo_url)}" alt="">`
                : `<div class="rapido-producto-thumb-placeholder">${RAPIDO_PLACEHOLDER_SVG}</div>`;
            const seleccionado = p.id === productoActualId ? " selected" : "";
            return `<div class="rapido-producto-item${seleccionado}" onmousedown="event.preventDefault(); seleccionarProductoRapido(${p.id})">
                ${thumb}
                <div class="rapido-producto-info">
                    <div class="rapido-producto-nombre">${escHtml(p.name)}</div>
                    <div class="rapido-producto-precio">Stock: ${p.current_stock || 0} — ${money(p.sale_price)}</div>
                </div>
            </div>`;
        }).join("");
    }

    contenedor.classList.add("visible");
}

function seleccionarProductoRapido(id) {
    const prod = catalogos.productos.find(p => p.id === id);
    if (!prod) return;

    document.getElementById("rapido-producto-id").value = String(prod.id);
    document.getElementById("rapido-producto-buscar").value = prod.name;
    ocultarResultadosProductoRapido();
    autoFillPrecioRapido();
}

function ocultarResultadosProductoRapido() {
    const contenedor = document.getElementById("rapido-producto-resultados");
    if (contenedor) contenedor.classList.remove("visible");
}

document.addEventListener("click", (e) => {
    const campo = document.getElementById("rapido-campo-producto");
    if (campo && !campo.contains(e.target)) {
        ocultarResultadosProductoRapido();
    }
    const campoCliente = document.getElementById("nueva-campo-cliente");
    if (campoCliente && !campoCliente.contains(e.target)) {
        ocultarResultadosClienteNueva();
    }
});

// ── PICKER DE CLIENTE (nueva comanda) — mismo patrón tipo-y-filtra ────────────
function filtrarClientesNueva() {
    const q = document.getElementById("nueva-cliente-buscar").value.trim().toLowerCase();
    const contenedor = document.getElementById("nueva-cliente-resultados");

    const clienteActualId = parseInt(document.getElementById("nueva-cliente-id").value);
    const coincidencias = catalogos.clientes
        .filter(c => c.full_name.toLowerCase().includes(q))
        .slice(0, 30);

    if (!coincidencias.length) {
        contenedor.innerHTML = '<div class="rapido-producto-vacio">Sin clientes que coincidan.</div>';
    } else {
        contenedor.innerHTML = coincidencias.map(c => {
            const seleccionado = c.id === clienteActualId ? " selected" : "";
            return `<div class="rapido-producto-item${seleccionado}" onmousedown="event.preventDefault(); seleccionarClienteNueva(${c.id})">
                <div class="rapido-producto-info">
                    <div class="rapido-producto-nombre">${escHtml(c.full_name)}</div>
                    ${c.phone ? `<div class="rapido-producto-precio">${escHtml(c.phone)}</div>` : ""}
                </div>
            </div>`;
        }).join("");
    }

    contenedor.classList.add("visible");
}

function seleccionarClienteNueva(id) {
    const cliente = catalogos.clientes.find(c => c.id === id);
    if (!cliente) return;

    document.getElementById("nueva-cliente-id").value = String(cliente.id);
    document.getElementById("nueva-cliente-buscar").value = cliente.full_name;
    ocultarResultadosClienteNueva();
}

function ocultarResultadosClienteNueva() {
    const contenedor = document.getElementById("nueva-cliente-resultados");
    if (contenedor) contenedor.classList.remove("visible");
}

async function confirmarRapido() {
    setError("error-rapido", "");

    const barberoId = parseInt(document.getElementById("rapido-barbero").value) || null;
    const metodo    = document.getElementById("rapido-metodo").value;
    const montoStr  = document.getElementById("rapido-monto").value.trim();
    const nota      = document.getElementById("rapido-nota").value.trim() || null;

    if (!barberoId) { setError("error-rapido", "Selecciona el barbero."); return; }

    const body = {
        tipo: rapidoTipoActual,
        barber_id: barberoId,
        payment_method: metodo,
        note: nota
    };

    if (rapidoTipoActual === "corte") {
        const servicioId = parseInt(document.getElementById("rapido-servicio").value) || null;
        if (!servicioId) { setError("error-rapido", "Selecciona el servicio."); return; }
        body.service_id = servicioId;
        body.quantity = 1;
    } else {
        const productoId = parseInt(document.getElementById("rapido-producto-id").value) || null;
        const cantidad = parseInt(document.getElementById("rapido-cantidad").value);
        if (!productoId) { setError("error-rapido", "Selecciona el producto."); return; }
        if (!cantidad || cantidad < 1) { setError("error-rapido", "La cantidad debe ser al menos 1."); return; }
        body.product_id = productoId;
        body.quantity = cantidad;
    }

    if (montoStr !== "") {
        const monto = parseFloat(montoStr);
        if (isNaN(monto) || monto < 0) { setError("error-rapido", "Monto recibido inválido."); return; }
        body.payment_amount = monto;
    }

    if (catalogos.cajaAbierta) {
        body.cash_register_id = catalogos.cajaAbierta.id;
    }

    setDisabled("btn-confirm-rapido", true, "Registrando...");

    try {
        const o = await window.api.apiRequest("/api/orders/quick-register", { method: "POST", body });
        cerrarModal("modal-rapido");
        alert(`Registrado — Comanda #${o.id} por ${money(o.total)}.`);
        mostrarVista("lista");
        await cargarLista();
    } catch (err) {
        setError("error-rapido", err.message);
        setDisabled("btn-confirm-rapido", false, "Registrar");
    }
}

// ── MODAL AGREGAR ÍTEM ────────────────────────────────────────────────────────
async function mostrarModalItem() {
    document.getElementById("item-tipo").value     = "servicio";
    document.getElementById("item-cantidad").value = "1";
    document.getElementById("item-precio").value   = "";
    // Abrir el modal de inmediato con estado de carga; el confirm queda bloqueado
    setError("error-item", "Cargando catálogos...");
    setDisabled("btn-confirm-item", true, "Cargando...");
    actualizarSelectItem();
    abrirModal("modal-item");

    await cargarCatalogos();          // Promise.allSettled interno: nunca lanza

    actualizarSelectItem();           // repobla el select con datos frescos
    setError("error-item", "");
    setDisabled("btn-confirm-item", false, "Agregar");
}

async function confirmarAgregarItem() {
    const tipo     = document.getElementById("item-tipo").value;
    const selectId = parseInt(document.getElementById("item-select").value);
    const cantidad = parseInt(document.getElementById("item-cantidad").value);
    const precio   = parseFloat(document.getElementById("item-precio").value);

    if (!selectId) { setError("error-item", "Selecciona un servicio o producto."); return; }
    if (!cantidad || cantidad < 1) { setError("error-item", "La cantidad debe ser al menos 1."); return; }
    if (isNaN(precio) || precio < 0) { setError("error-item", "Ingresa un precio válido."); return; }

    const body = { item_type: tipo, quantity: cantidad, unit_price: precio };
    if (tipo === "servicio") body.service_id = selectId;
    else                     body.product_id = selectId;

    setDisabled("btn-confirm-item", true, "Agregando...");
    setError("error-item", "");

    try {
        const o = await window.api.apiRequest(`/api/orders/${comandaActual.id}/items`, {
            method: "POST",
            body
        });
        comandaActual = o;
        cerrarModal("modal-item");
        renderDetalle();
    } catch (err) {
        setError("error-item", err.message);
        setDisabled("btn-confirm-item", false, "Agregar");
    }
}

// ── ELIMINAR ÍTEM ─────────────────────────────────────────────────────────────
async function eliminarItem(itemId) {
    if (!confirm("¿Eliminar este ítem de la comanda?")) return;
    setError("error-detalle", "");
    try {
        const o = await window.api.apiRequest(
            `/api/orders/${comandaActual.id}/items/${itemId}`,
            { method: "DELETE" }
        );
        comandaActual = o;
        renderDetalle();
    } catch (err) {
        setError("error-detalle", err.message);
    }
}

// ── MODAL COBRAR ──────────────────────────────────────────────────────────────
function mostrarModalCobrar() {
    const o = comandaActual;
    document.getElementById("cobrar-barbero").value = o.barber_id || "";
    document.getElementById("cobrar-metodo").value  = "efectivo";
    document.getElementById("cobrar-monto").value   = "";
    document.getElementById("cobrar-nota").value    = "";
    setError("error-cobrar", "");

    const pagoSection = document.getElementById("cobrar-pago-section");
    if (pagoSection) pagoSection.style.display = o.is_fiado ? "none" : "block";

    const info = document.getElementById("cobrar-info");
    if (info) {
        info.innerHTML = o.is_fiado
            ? '<span style="color:#ffb74d;">⚠ Comanda fiada: se cerrará sin cobro inmediato y quedará pendiente en Cuentas.</span>'
            : `Total a cobrar: <strong style="color:var(--gold);font-size:1.05rem;">${money(o.total)}</strong>` +
              (catalogos.cajaAbierta
                  ? `<br><small style="color:#81c784;">✔ Caja abierta #${catalogos.cajaAbierta.id}</small>`
                  : `<br><small style="color:#ef9a9a;">⚠ No hay caja abierta. El cobro puede fallar si no es fiado.</small>`);
    }

    setDisabled("btn-confirm-cobrar", false, "Confirmar Cobro");
    abrirModal("modal-cobrar");
}

async function confirmarCobrar() {
    const barberoId = parseInt(document.getElementById("cobrar-barbero").value) || null;
    const nota      = document.getElementById("cobrar-nota").value.trim() || null;
    const esFiado   = comandaActual.is_fiado;

    const body = { barber_id: barberoId, note: nota };

    if (!esFiado) {
        const metodo   = document.getElementById("cobrar-metodo").value;
        const montoStr = document.getElementById("cobrar-monto").value.trim();
        body.payment_method = metodo;

        if (montoStr !== "") {
            const monto = parseFloat(montoStr);
            if (isNaN(monto) || monto < 0) {
                setError("error-cobrar", "Monto recibido inválido.");
                return;
            }
            body.payment_amount = monto;
        }

        if (catalogos.cajaAbierta) {
            body.cash_register_id = catalogos.cajaAbierta.id;
        }
    }

    setDisabled("btn-confirm-cobrar", true, "Procesando...");
    setError("error-cobrar", "");

    try {
        const o = await window.api.apiRequest(`/api/orders/${comandaActual.id}/close`, {
            method: "PATCH",
            body
        });
        comandaActual = o;
        cerrarModal("modal-cobrar");
        renderDetalle();
        cargarLista();
    } catch (err) {
        setError("error-cobrar", err.message);
        setDisabled("btn-confirm-cobrar", false, "Confirmar Cobro");
    }
}

// ── CANCELAR COMANDA ──────────────────────────────────────────────────────────
async function cancelarComanda() {
    if (!confirm(`¿Cancelar comanda #${comandaActual.id}? Esta acción no se puede deshacer.`)) return;
    setError("error-detalle", "");
    try {
        const o = await window.api.apiRequest(`/api/orders/${comandaActual.id}/cancel`, {
            method: "PATCH"
        });
        comandaActual = o;
        renderDetalle();
        cargarLista();
    } catch (err) {
        setError("error-detalle", err.message);
    }
}

// ── NAVEGACIÓN ────────────────────────────────────────────────────────────────
function mostrarVista(nombre) {
    document.getElementById("vista-lista").style.display   = nombre === "lista"   ? "block" : "none";
    document.getElementById("vista-detalle").style.display = nombre === "detalle" ? "block" : "none";
    document.getElementById("btn-volver").style.display    = nombre === "detalle" ? "inline-block" : "none";
    document.getElementById("btn-nueva").style.display     = nombre === "lista"   ? "inline-block" : "none";
}

async function volverALista() {
    comandaActual = null;
    mostrarVista("lista");
    await cargarLista();
}

// ── MODALES ───────────────────────────────────────────────────────────────────
function abrirModal(id)  { document.getElementById(id).classList.add("visible"); }
function cerrarModal(id) { document.getElementById(id).classList.remove("visible"); }

// ── STATUS HELPERS ────────────────────────────────────────────────────────────
function statusBadge(status) {
    const map = {
        abierta:   { clase: "partial", label: "Abierta"   },
        cerrada:   { clase: "paid",    label: "Cerrada"   },
        cancelada: { clase: "pending", label: "Cancelada" },
    };
    return map[status] || { clase: "", label: status };
}

function payStatusBadge(ps, esFiado) {
    if (esFiado) return { clase: "partial", label: "Fiado" };
    const map = {
        pendiente: { clase: "pending", label: "Pendiente" },
        pagada:    { clase: "paid",    label: "Pagada"    },
        parcial:   { clase: "partial", label: "Parcial"   },
        fiado:     { clase: "partial", label: "Fiado"     },
    };
    return map[ps] || { clase: "", label: ps };
}

// ── UTILS ─────────────────────────────────────────────────────────────────────
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
    el.disabled    = disabled;
    el.textContent = label;
}

function money(n) {
    if (n == null) return "—";
    return "$ " + Number(n).toLocaleString("es-CO", { minimumFractionDigits: 0 });
}

function fmt(n) {
    if (n == null) return "0";
    return Number(n).toLocaleString("es-CO", { minimumFractionDigits: 0 });
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
