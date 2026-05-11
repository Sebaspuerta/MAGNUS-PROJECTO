async function loadClients() {
  const pageContent = document.getElementById("page-content");
  if (!pageContent) return;

  pageContent.innerHTML = `
    <div class="panel">
      <div class="panel-header"><h3>Cargando clientes...</h3></div>
    </div>
  `;

  try {
    const clients = await window.api.apiRequest("/api/clients");
    const rows = clients.length === 0
      ? `<tr><td colspan="6">No hay clientes registrados.</td></tr>`
      : clients.map((client) => `
        <tr>
          <td>${client.id}</td>
          <td>${client.full_name}</td>
          <td>${client.phone || "-"}</td>
          <td>${client.email || "-"}</td>
          <td>${client.document_number || "-"}</td>
          <td>${client.is_active ? "Activo" : "Inactivo"}</td>
        </tr>
      `).join("");

    pageContent.innerHTML = `
      <div class="panel">
        <div class="panel-header"><h3>Clientes</h3></div>
        <div class="table-wrapper">
          <table class="table-block">
            <thead>
              <tr>
                <th>ID</th>
                <th>Nombre</th>
                <th>Teléfono</th>
                <th>Email</th>
                <th>Documento</th>
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
  } catch (error) {
    showPageError(error.message || "No se pudo cargar los clientes.");
  }
}

window.loadClients = loadClients;
