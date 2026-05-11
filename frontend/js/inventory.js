function renderInventoryPage(products) {
  const pageContent = document.getElementById("page-content");
  if (!pageContent) return;

  let rows = "";
  if (products.length === 0) {
    rows = `<tr><td colspan="7">No hay productos en inventario.</td></tr>`;
  } else {
    rows = products.map((product) => {
      const expiration = product.expiration_date || "-";
      return `
        <tr>
          <td>${product.id}</td>
          <td>${product.name}</td>
          <td>${product.category || "-"}</td>
          <td>${product.product_type}</td>
          <td>${product.current_stock}</td>
          <td>$${Number(product.sale_price).toLocaleString("es-CO")}</td>
          <td>${product.is_active ? "Activo" : "Inactivo"}</td>
        </tr>
      `;
    }).join("");
  }

  pageContent.innerHTML = `
    <div class="panel">
      <div class="panel-header">
        <h3>Inventario de productos</h3>
      </div>
      <div class="table-wrapper">
        <table class="table-block">
          <thead>
            <tr>
              <th>ID</th>
              <th>Nombre</th>
              <th>Categoría</th>
              <th>Tipo</th>
              <th>Stock</th>
              <th>Precio</th>
              <th>Estado</th>
            </tr>
          </thead>
          <tbody>
            ${rows}
          </tbody>
        </table>
      </div>
    </div>
  `;
}

async function loadInventory() {
  const pageContent = document.getElementById("page-content");
  if (!pageContent) return;

  pageContent.innerHTML = `
    <div class="panel">
      <div class="panel-header"><h3>Cargando inventario...</h3></div>
    </div>
  `;

  try {
    const products = await window.api.apiRequest("/api/inventory/products");
    renderInventoryPage(products || []);
  } catch (error) {
    showPageError(error.message || "No se pudo cargar el inventario.");
  }
}

window.loadInventory = loadInventory;
