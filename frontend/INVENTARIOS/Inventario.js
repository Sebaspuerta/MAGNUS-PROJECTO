let categorias = [];
let categoriaActual = null; // { id, name } o null si estamos en la vista home
let todosLosProductos = [];
let fotoSeleccionadaFile = null;

// ── INIT ───────────────────────────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
    const isOwner = ["mateo", "admin"].includes(((window.api.getAuthUser() || {}).username || "").toLowerCase());
    const btnCat = document.getElementById("btn-categorias");
    if (btnCat) btnCat.style.display = isOwner ? "inline-flex" : "none";

    cargarCategorias();
});

// ══════════════════════════════════════════════════════════════════════════════
// CATEGORÍAS
// ══════════════════════════════════════════════════════════════════════════════

async function cargarCategorias() {
    setError("error-home", "");
    const msg = document.getElementById("msg-carga-categorias");
    if (msg) { msg.textContent = "Cargando categorías..."; msg.style.display = "block"; }

    try {
        categorias = await window.api.apiRequest("/api/categories");
        if (msg) msg.style.display = "none";
        renderCategorias(categorias);
    } catch (err) {
        if (msg) msg.textContent = "Error al cargar: " + err.message;
        setError("error-home", err.message);
    }
}

function renderCategorias(lista) {
    const grid = document.getElementById("grid-categorias");

    if (!lista.length) {
        grid.innerHTML = '<div style="color:var(--muted);padding:8px 0;">Sin categorías. Crea la primera con el botón Categorías.</div>';
        return;
    }

    grid.innerHTML = lista.map(c => `<div class="card category-card" onclick="abrirCategoria(${c.id}, '${escAttr(c.name)}')">
            <div class="category-icon"><i data-lucide="folder"></i></div>
            <div class="category-name">${escHtml(c.name)}</div>
            <div class="category-count">${c.product_count} producto${c.product_count === 1 ? "" : "s"}</div>
        </div>`).join("");

    lucide.createIcons();
}

function abrirCategoria(id, name) {
    categoriaActual = { id, name };
    setText("categoria-actual-nombre", name);
    document.getElementById("vista-home").style.display      = "none";
    document.getElementById("vista-categoria").style.display = "block";
    cargarProductos();
}

function volverAHome() {
    categoriaActual = null;
    document.getElementById("vista-categoria").style.display = "none";
    document.getElementById("vista-home").style.display      = "block";
    cargarCategorias();
}

// ── MODAL GESTIONAR CATEGORÍAS (crear / eliminar, punto único de entrada) ──────
let categoriaAEliminar = null; // { id, name } mientras se elige qué pasa con sus productos

function abrirModalCategorias() {
    mostrarPasoElegirCategoria();
    abrirModal("modal-categorias");
}

function mostrarPasoElegirCategoria() {
    categoriaAEliminar = null;
    document.getElementById("cat-paso-elegir").style.display        = "block";
    document.getElementById("cat-paso-crear").style.display         = "none";
    document.getElementById("cat-paso-eliminar").style.display      = "none";
    document.getElementById("cat-paso-eliminar-modo").style.display = "none";
}

function mostrarPasoCrearCategoria() {
    document.getElementById("cat-name").value = "";
    setError("error-categoria", "");
    setDisabled("btn-guardar-categoria", false, "Guardar");

    document.getElementById("cat-paso-elegir").style.display        = "none";
    document.getElementById("cat-paso-crear").style.display         = "block";
    document.getElementById("cat-paso-eliminar").style.display      = "none";
    document.getElementById("cat-paso-eliminar-modo").style.display = "none";
}

async function guardarCategoria() {
    const nombre = document.getElementById("cat-name").value.trim();
    if (!nombre) { setError("error-categoria", "El nombre es obligatorio."); return; }

    setDisabled("btn-guardar-categoria", true, "Guardando...");
    setError("error-categoria", "");

    try {
        await window.api.apiRequest("/api/categories", { method: "POST", body: { name: nombre } });
        cerrarModal("modal-categorias");
        await cargarCategorias();
    } catch (err) {
        setError("error-categoria", err.message);
        setDisabled("btn-guardar-categoria", false, "Guardar");
    }
}

function mostrarPasoEliminarCategoria() {
    categoriaAEliminar = null;
    setError("error-categoria-eliminar", "");
    renderListaEliminarCategorias();

    document.getElementById("cat-paso-elegir").style.display        = "none";
    document.getElementById("cat-paso-crear").style.display         = "none";
    document.getElementById("cat-paso-eliminar").style.display      = "block";
    document.getElementById("cat-paso-eliminar-modo").style.display = "none";
}

function renderListaEliminarCategorias() {
    const cont   = document.getElementById("cat-eliminar-lista");
    const reales = categorias.filter(c => c.id != null); // nunca "Sin categoría": no es real, no se borra

    if (!reales.length) {
        cont.innerHTML = '<div style="color:var(--muted);padding:8px 0;">No hay categorías para eliminar.</div>';
        return;
    }

    cont.innerHTML = reales.map(c => `
        <div class="cat-eliminar-item">
            <div>
                <div class="cat-eliminar-nombre">${escHtml(c.name)}</div>
                <div class="cat-eliminar-count">${c.product_count} producto${c.product_count === 1 ? "" : "s"}</div>
            </div>
            <button class="danger" onclick="prepararEliminarCategoria(${c.id}, '${escAttr(c.name)}')">Eliminar</button>
        </div>
    `).join("");
}

// Paso intermedio: preguntar qué pasa con los productos antes de ejecutar nada.
function prepararEliminarCategoria(id, nombre) {
    categoriaAEliminar = { id, name: nombre };
    setText("cat-eliminar-modo-nombre", `"${nombre}"`);
    setError("error-categoria-eliminar-modo", "");

    document.getElementById("cat-paso-elegir").style.display        = "none";
    document.getElementById("cat-paso-crear").style.display         = "none";
    document.getElementById("cat-paso-eliminar").style.display      = "none";
    document.getElementById("cat-paso-eliminar-modo").style.display = "block";
}

async function confirmarEliminarCategoria(conProductos) {
    if (!categoriaAEliminar) return;
    const { id, name } = categoriaAEliminar;

    const msg = conProductos
        ? `¿Eliminar la categoría "${name}" Y TODOS sus productos? Los productos se marcarán como ` +
          `eliminados (su historial de ventas y movimientos ya registrado se conserva intacto). ` +
          `Esta acción no se puede deshacer.`
        : `¿Eliminar la categoría "${name}"? Sus productos pasarán automáticamente a "Sin categoría" — ` +
          `no se eliminan ni pierden datos (ventas, stock, movimientos). Esta acción no se puede deshacer.`;
    if (!confirm(msg)) return;

    setError("error-categoria-eliminar-modo", "");
    try {
        await window.api.apiRequest(`/api/categories/${id}?delete_products=${conProductos}`, { method: "DELETE" });
        categoriaAEliminar = null;
        await cargarCategorias();
        mostrarPasoEliminarCategoria();
    } catch (err) {
        const detail = err.responseData && err.responseData.detail;
        setError("error-categoria-eliminar-modo", (typeof detail === "string" ? detail : null) || err.message);
    }
}

// ══════════════════════════════════════════════════════════════════════════════
// PRODUCTOS (dentro de una categoría)
// ══════════════════════════════════════════════════════════════════════════════

async function cargarProductos() {
    if (!categoriaActual) return;
    setError("error-global", "");
    const msg = document.getElementById("msg-carga");
    if (msg) { msg.textContent = "Cargando inventario..."; msg.style.display = "block"; }

    try {
        const filtroCategoria = categoriaActual.id == null
            ? "uncategorized=true"
            : `category_id=${categoriaActual.id}`;
        todosLosProductos = await window.api.apiRequest(
            `/api/inventory/products?include_inactive=true&${filtroCategoria}`
        );
        if (msg) msg.style.display = "none";
        renderGrid(todosLosProductos);
    } catch (err) {
        if (msg) msg.textContent = "Error al cargar: " + err.message;
        setError("error-global", err.message);
    }
}

// ── RENDER GRID ────────────────────────────────────────────────────────────────
function renderGrid(lista) {
    const grid = document.getElementById("grid");

    if (!lista.length) {
        grid.innerHTML = '<div style="grid-column:1/-1;color:var(--muted);padding:8px 0;">Sin productos en esta categoría. Crea el primero con + Producto.</div>';
        return;
    }

    grid.innerHTML = lista.map(p => {
        const { badgeClass, badgeLabel } = stockBadge(p);
        const precioVenta = money(p.sale_price);
        const tipo = tipoLabel(p.product_type);
        const stockColor = p.current_stock === 0 ? 'var(--red)' : p.current_stock <= (p.minimum_stock || 0) ? 'var(--orange)' : 'var(--green)';

        const expAlert = vencimientoAlert(p);

        const thumbHtml = p.photo_url
            ? `<img class="thumb" src="${escAttr(p.photo_url)}" alt="">`
            : `<div class="thumb-placeholder"><i data-lucide="package"></i></div>`;

        return `<div class="card product-card${p.is_active ? '' : ' inactive'}">
            <button class="product-menu-btn" onclick="event.stopPropagation(); toggleProductMenu(${p.id}, this)" title="Acciones" aria-label="Acciones del producto">
                <i data-lucide="more-vertical"></i>
            </button>

            <div class="product-photo-frame">${thumbHtml}</div>

            <div class="title" title="${escAttr(p.name)}">${escHtml(p.name)}</div>
            <div class="product-price">${precioVenta}</div>

            <div class="product-meta-row">
                <span class="badge ${badgeClass}">${badgeLabel}</span>
                <span class="product-stock">Stock: <strong style="color:${stockColor}">${p.current_stock}</strong>${p.minimum_stock != null ? ` / ${p.minimum_stock}` : ''}</span>
            </div>

            <div class="meta" style="color:var(--gold);font-size:.7rem;">${escHtml(tipo)}</div>
            ${p.expiration_date ? `<div class="meta">📅 Vence: ${p.expiration_date}</div>` : ''}
            ${expAlert}
            ${!p.is_active ? '<div class="meta" style="color:var(--red);">Inactivo</div>' : ''}
        </div>`;
    }).join("");

    lucide.createIcons();
}

// ── MENÚ DE ACCIONES (⋮) ──────────────────────────────────────────────────────
let menuAbiertoProductoId = null;

function accionesDelProducto(id) {
    const p = todosLosProductos.find(x => x.id === id);
    if (!p) return [];

    const isOwner = ["mateo", "admin"].includes(((window.api.getAuthUser() || {}).username || "").toLowerCase());
    const nombre = escAttr(p.name);

    const acciones = p.is_active ? [
        { label: "Editar",          icon: "pencil",            onclick: `abrirModalEditar(${p.id})` },
        { label: "Agregar stock",   icon: "plus-circle",       onclick: `mostrarModalEntrada(${p.id}, '${nombre}')`, className: "accion-stock" },
        { label: "Ver movimientos", icon: "history",           onclick: `verMovimientos(${p.id}, '${nombre}')` },
        { label: "Dar de baja",     icon: "arrow-down-circle", onclick: `desactivar(${p.id}, '${nombre}')`, className: "accion-danger" },
    ] : [
        { label: "Ver movimientos", icon: "history", onclick: `verMovimientos(${p.id}, '${nombre}')` },
    ];

    if (isOwner) {
        acciones.push({ label: "Eliminar", icon: "trash-2", onclick: `eliminarProducto(${p.id}, '${nombre}')`, className: "accion-danger" });
    }

    return acciones;
}

function toggleProductMenu(id, btnEl) {
    if (menuAbiertoProductoId === id) {
        cerrarProductMenu();
        return;
    }

    const dropdown = document.getElementById("product-menu-dropdown");
    const acciones = accionesDelProducto(id);

    dropdown.innerHTML = acciones.map(a =>
        `<button class="product-menu-item ${a.className || ''}" onclick="cerrarProductMenu(); ${a.onclick}">
            <i data-lucide="${a.icon}"></i> ${a.label}
        </button>`
    ).join("");

    const rect = btnEl.getBoundingClientRect();
    dropdown.style.top  = `${rect.bottom + 6}px`;
    dropdown.style.left = `${Math.max(8, rect.right - 178)}px`;
    dropdown.classList.add("open");
    menuAbiertoProductoId = id;

    lucide.createIcons();
}

function cerrarProductMenu() {
    const dropdown = document.getElementById("product-menu-dropdown");
    if (!dropdown) return;
    dropdown.classList.remove("open");
    dropdown.innerHTML = "";
    menuAbiertoProductoId = null;
}

document.addEventListener("click", (e) => {
    if (menuAbiertoProductoId === null) return;
    const dropdown = document.getElementById("product-menu-dropdown");
    if (dropdown.contains(e.target)) return;
    cerrarProductMenu();
});

window.addEventListener("scroll", () => cerrarProductMenu(), true);

function stockBadge(p) {
    if (!p.is_active)                                      return { badgeClass: "low",  badgeLabel: "INACTIVO" };
    if (p.current_stock === 0)                             return { badgeClass: "low",  badgeLabel: "AGOTADO"  };
    if (p.minimum_stock != null && p.current_stock <= p.minimum_stock)
                                                           return { badgeClass: "exp",  badgeLabel: "BAJO"     };
    return { badgeClass: "good", badgeLabel: "OK" };
}

function vencimientoAlert(p) {
    if (!p.expiration_date || !p.is_active) return "";
    const dias = (new Date(p.expiration_date) - new Date()) / 86400000;
    if (dias < 0)  return `<div class="alert">⚠ Producto vencido</div>`;
    if (dias < 8)  return `<div class="alert">⚠ Vence en ${Math.ceil(dias)} días</div>`;
    return "";
}

function tipoLabel(tipo) {
    const map = { venta: "Venta", consumible_interno: "Consumible interno", perecedero: "Perecedero" };
    return map[tipo] || tipo || "—";
}

// ── FOTO (preview local + subida tras guardar) ─────────────────────────────────
function resetFotoPicker(photoUrl) {
    fotoSeleccionadaFile = null;
    document.getElementById("f-photo").value = "";
    const img = document.getElementById("foto-preview-img");
    const placeholder = document.getElementById("foto-preview-placeholder");
    if (photoUrl) {
        img.src = photoUrl;
        img.style.display = "block";
        placeholder.style.display = "none";
    } else {
        img.style.display = "none";
        img.src = "";
        placeholder.style.display = "block";
    }
}

function previewFotoSeleccionada() {
    const input = document.getElementById("f-photo");
    const file  = input.files && input.files[0];
    if (!file) return;

    fotoSeleccionadaFile = file;

    const reader = new FileReader();
    reader.onload = () => {
        const img = document.getElementById("foto-preview-img");
        img.src = reader.result;
        img.style.display = "block";
        document.getElementById("foto-preview-placeholder").style.display = "none";
    };
    reader.readAsDataURL(file);
}

async function subirFotoProducto(id) {
    if (!fotoSeleccionadaFile) return;

    const formData = new FormData();
    formData.append("photo", fotoSeleccionadaFile);

    const token = window.api.getAuthToken();
    const resp = await fetch(window.api.buildUrl(`/api/inventory/products/${id}/photo`), {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
        body: formData
    });

    if (!resp.ok) {
        const data = await resp.json().catch(() => null);
        const detail = data && data.detail;
        throw new Error((typeof detail === "string" ? detail : null) || "No se pudo subir la foto.");
    }
}

// ── SELECT DE CATEGORÍA (modal producto) ───────────────────────────────────────
function poblarSelectCategorias(selectedId) {
    const sel = document.getElementById("f-category");
    sel.innerHTML = '<option value="">Sin categoría</option>' +
        categorias.filter(c => c.id != null).map(c => `<option value="${c.id}">${escHtml(c.name)}</option>`).join("");
    sel.value = selectedId != null ? String(selectedId) : "";
}

// ── MODAL CREAR ────────────────────────────────────────────────────────────────
function abrirModalNuevo() {
    setText("modal-titulo", "Nuevo Producto");
    document.getElementById("edit-id").value        = "";
    document.getElementById("f-name").value         = "";
    document.getElementById("f-type").value         = "venta";
    document.getElementById("f-desc").value         = "";
    document.getElementById("f-sale-price").value   = "";
    document.getElementById("f-purchase-cost").value= "";
    document.getElementById("f-stock").value        = "0";
    document.getElementById("f-min-stock").value    = "";
    document.getElementById("f-expiry").value       = "";
    document.getElementById("stock-inicial-section").style.display = "block";
    poblarSelectCategorias(categoriaActual ? categoriaActual.id : null);
    resetFotoPicker(null);
    setError("error-producto", "");
    setDisabled("btn-guardar", false, "Guardar");
    abrirModal("modal-producto");
}

// ── MODAL EDITAR ───────────────────────────────────────────────────────────────
async function abrirModalEditar(id) {
    setError("error-producto", "");
    setError("error-global",   "");
    try {
        const p = await window.api.apiRequest(`/api/inventory/products/${id}`);
        setText("modal-titulo", "Editar Producto");
        document.getElementById("edit-id").value        = p.id;
        document.getElementById("f-name").value         = p.name            || "";
        document.getElementById("f-type").value         = p.product_type    || "venta";
        document.getElementById("f-desc").value         = p.description     || "";
        document.getElementById("f-sale-price").value   = p.sale_price      ?? "";
        document.getElementById("f-purchase-cost").value= p.purchase_cost   ?? "";
        document.getElementById("f-min-stock").value    = p.minimum_stock   ?? "";
        document.getElementById("f-expiry").value       = p.expiration_date || "";
        document.getElementById("stock-inicial-section").style.display = "none";
        poblarSelectCategorias(p.category_id);
        resetFotoPicker(p.photo_url || null);
        setError("error-producto", "");
        setDisabled("btn-guardar", false, "Guardar Cambios");
        abrirModal("modal-producto");
    } catch (err) {
        setError("error-global", "No se pudo cargar el producto: " + err.message);
    }
}

// ── GUARDAR (crear o editar) ──────────────────────────────────────────────────
async function guardarProducto() {
    const id         = document.getElementById("edit-id").value;
    const nombre     = document.getElementById("f-name").value.trim();
    const categoryR  = document.getElementById("f-category").value;
    const tipo       = document.getElementById("f-type").value;
    const desc       = document.getElementById("f-desc").value.trim() || null;
    const salePriceR = document.getElementById("f-sale-price").value;
    const purchaseR  = document.getElementById("f-purchase-cost").value;
    const stockR     = document.getElementById("f-stock").value;
    const minStockR  = document.getElementById("f-min-stock").value;
    const expiry     = document.getElementById("f-expiry").value || null;

    if (!nombre) { setError("error-producto", "El nombre es obligatorio."); return; }
    if (!tipo)   { setError("error-producto", "Selecciona el tipo de producto."); return; }

    const salePrice = parseFloat(salePriceR);
    if (isNaN(salePrice) || salePrice < 0) { setError("error-producto", "Precio de venta inválido."); return; }

    const body = {
        name:             nombre,
        category_id:      categoryR ? parseInt(categoryR) : null,
        product_type:     tipo,
        description:      desc,
        sale_price:       salePrice,
        purchase_cost:    purchaseR ? parseFloat(purchaseR) : 0,
        minimum_stock:    minStockR ? parseInt(minStockR) : null,
        expiration_date:  expiry,
    };

    if (!id) {
        body.current_stock = stockR ? parseInt(stockR) : 0;
    }

    const btnLabel = id ? "Guardar Cambios" : "Guardar";
    setDisabled("btn-guardar", true, "Guardando...");
    setError("error-producto", "");

    try {
        let productoId = id;
        if (id) {
            await window.api.apiRequest(`/api/inventory/products/${id}`, { method: "PATCH", body });
        } else {
            const creado = await window.api.apiRequest("/api/inventory/products", { method: "POST", body });
            productoId = creado.id;
        }

        if (fotoSeleccionadaFile) {
            try {
                await subirFotoProducto(productoId);
            } catch (fotoErr) {
                cerrarModal("modal-producto");
                await cargarProductos();
                setError("error-global", "El producto se guardó, pero la foto no se pudo subir: " + fotoErr.message);
                return;
            }
        }

        cerrarModal("modal-producto");
        await cargarProductos();
    } catch (err) {
        setError("error-producto", err.message);
        setDisabled("btn-guardar", false, btnLabel);
    }
}

// ── ELIMINAR (solo el dueño, Mateo) ────────────────────────────────────────────
async function eliminarProducto(id, nombre) {
    const msg = `Esto ocultará "${nombre}" de todo el sistema para uso futuro. ` +
        `El historial de ventas ya registrado se conserva, pero se marcará como eliminado. ` +
        `Esta acción no se puede deshacer. ¿Continuar?`;
    if (!confirm(msg)) return;
    setError("error-global", "");
    try {
        await window.api.apiRequest(`/api/inventory/products/${id}`, { method: "DELETE" });
        await cargarProductos();
    } catch (err) {
        const detail = err.responseData && err.responseData.detail;
        setError("error-global", (typeof detail === "string" ? detail : null) || err.message);
    }
}

// ── DESACTIVAR ────────────────────────────────────────────────────────────────
async function desactivar(id, nombre) {
    if (!confirm(`¿Dar de baja "${nombre}"? Dejará de aparecer en Comandas.`)) return;
    setError("error-global", "");
    try {
        await window.api.apiRequest(`/api/inventory/products/${id}/deactivate`, { method: "PATCH" });
        await cargarProductos();
    } catch (err) {
        setError("error-global", err.message);
    }
}

// ── MODAL ENTRADA DE STOCK ────────────────────────────────────────────────────
function mostrarModalEntrada(id, nombre) {
    document.getElementById("entrada-id").value    = id;
    document.getElementById("entrada-nombre").textContent = nombre;
    document.getElementById("entrada-qty").value   = "";
    document.getElementById("entrada-reason").value= "";
    setError("error-entrada", "");
    setDisabled("btn-confirmar-entrada", false, "Confirmar Entrada");
    abrirModal("modal-entrada");
}

async function confirmarEntrada() {
    const id     = document.getElementById("entrada-id").value;
    const qty    = parseInt(document.getElementById("entrada-qty").value);
    const reason = document.getElementById("entrada-reason").value.trim();

    if (!qty || qty < 1) { setError("error-entrada", "Ingresa una cantidad mayor a 0."); return; }
    if (!reason)         { setError("error-entrada", "El motivo es obligatorio."); return; }

    setDisabled("btn-confirmar-entrada", true, "Registrando...");
    setError("error-entrada", "");

    try {
        await window.api.apiRequest(`/api/inventory/products/${id}/entry`, {
            method: "POST",
            body:   { quantity: qty, reason }
        });
        cerrarModal("modal-entrada");
        await cargarProductos();
    } catch (err) {
        setError("error-entrada", err.message);
        setDisabled("btn-confirmar-entrada", false, "Confirmar Entrada");
    }
}

// ── VER MOVIMIENTOS ───────────────────────────────────────────────────────────
async function verMovimientos(id, nombre) {
    setText("history-title", nombre);
    const msg   = document.getElementById("msg-movs");
    const tabla = document.getElementById("tabla-movs");
    const tbody = document.getElementById("history");

    msg.textContent    = "Cargando movimientos...";
    msg.style.display  = "block";
    tabla.style.display= "none";

    tabla.scrollIntoView({ behavior: "smooth", block: "start" });

    try {
        const movs = await window.api.apiRequest(`/api/inventory/products/${id}/movements`);

        if (!movs.length) {
            msg.textContent = "Sin movimientos registrados para este producto.";
            return;
        }

        msg.style.display  = "none";
        tabla.style.display= "table";

        tbody.innerHTML = movs.map(m => `
            <tr>
                <td>${escHtml(m.movement_type)}</td>
                <td style="color:${m.quantity > 0 ? 'var(--green)' : 'var(--red)'};font-weight:600;">${m.quantity > 0 ? '+' : ''}${m.quantity}</td>
                <td>${m.previous_stock}</td>
                <td>${m.new_stock}</td>
                <td>${escHtml(m.reason)}</td>
                <td style="font-size:.78rem;color:var(--muted);">${fmtFecha(m.created_at)}</td>
            </tr>
        `).join("");
    } catch (err) {
        msg.textContent = "Error: " + err.message;
    }
}

// ── MODAL HELPERS ─────────────────────────────────────────────────────────────
function abrirModal(id)  { document.getElementById(id).classList.add("active"); }
function cerrarModal(id) { document.getElementById(id).classList.remove("active"); }

// ── UTILS ─────────────────────────────────────────────────────────────────────
function setText(id, v)  { const e = document.getElementById(id); if (e) e.textContent = v; }
function setError(id, m) {
    const e = document.getElementById(id);
    if (!e) return;
    e.textContent = m;
    e.style.color = "";
}
function setInfo(id, m) {
    const e = document.getElementById(id);
    if (!e) return;
    e.textContent = m;
    e.style.color = "var(--amber, #E7A53C)";
}
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
function escAttr(s)  { return String(s).replace(/'/g, "\\'"); }