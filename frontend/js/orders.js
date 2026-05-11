async function loadOrders() {
  const pageContent = document.getElementById("page-content");
  if (!pageContent) return;

  pageContent.innerHTML = `
    <div class="panel">
      <div class="panel-header"><h3>Cargando comandas...</h3></div>
    </div>
  `;

  try {
    const orders = await window.api.apiRequest("/api/orders");
    const rows = orders.length === 0
      ? `<tr><td colspan="7">No hay comandas disponibles.</td></tr>`
      : orders.map((order) => `
        <tr>
          <td>${order.id}</td>
          <td>${order.client_id || "-"}</td>
          <td>${order.barber_id || "-"}</td>
          <td>${order.status}</td>
          <td>$${Number(order.total).toLocaleString("es-CO")}</td>
          <td>${order.created_at ? new Date(order.created_at).toLocaleString("es-CO") : "-"}</td>
          <td>${order.closed_at ? new Date(order.closed_at).toLocaleString("es-CO") : "-"}</td>
        </tr>
      `).join("");

    pageContent.innerHTML = `
      <div class="panel">
        <div class="panel-header"><h3>Comandas</h3></div>
        <div class="table-wrapper">
          <table class="table-block">
            <thead>
              <tr>
                <th>ID</th>
                <th>Cliente</th>
                <th>Barbero</th>
                <th>Estado</th>
                <th>Total</th>
                <th>Creada</th>
                <th>Cerrada</th>
              </tr>
            </thead>
            <tbody>
              ${rows}
            </tbody>
          </table>
        </div>
      </div>
    `;
  } catch (error) {
    showPageError(error.message || "No se pudo cargar las comandas.");
  }
}

window.loadOrders = loadOrders;
