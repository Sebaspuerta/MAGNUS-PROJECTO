async function loadServices() {
  const pageContent = document.getElementById("page-content");
  if (!pageContent) return;

  pageContent.innerHTML = `
    <div class="panel">
      <div class="panel-header"><h3>Cargando servicios...</h3></div>
    </div>
  `;

  try {
    const services = await window.api.apiRequest("/api/services");
    const rows = services.length === 0
      ? `<tr><td colspan="6">No hay servicios registrados.</td></tr>`
      : services.map((service) => `
        <tr>
          <td>${service.id}</td>
          <td>${service.name}</td>
          <td>${service.category || "-"}</td>
          <td>${service.price !== undefined ? `$${Number(service.price).toLocaleString("es-CO")}` : "-"}</td>
          <td>${service.estimated_duration_minutes || "-"}</td>
          <td>${service.is_active ? "Activo" : "Inactivo"}</td>
        </tr>
      `).join("");

    pageContent.innerHTML = `
      <div class="panel">
        <div class="panel-header"><h3>Servicios</h3></div>
        <div class="table-wrapper">
          <table class="table-block">
            <thead>
              <tr>
                <th>ID</th>
                <th>Nombre</th>
                <th>Categoría</th>
                <th>Precio</th>
                <th>Duración</th>
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
    showPageError(error.message || "No se pudo cargar los servicios.");
  }
}

window.loadServices = loadServices;
