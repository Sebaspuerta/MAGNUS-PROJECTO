async function loadBarbers() {
  const pageContent = document.getElementById("page-content");
  if (!pageContent) return;

  pageContent.innerHTML = `
    <div class="panel">
      <div class="panel-header"><h3>Cargando barberos...</h3></div>
    </div>
  `;

  try {
    const barbers = await window.api.apiRequest("/api/barbers");
    const rows = barbers.length === 0
      ? `<tr><td colspan="6">No hay barberos registrados.</td></tr>`
      : barbers.map((barber) => `
        <tr>
          <td>${barber.id}</td>
          <td>${barber.full_name}</td>
          <td>${barber.alias || "-"}</td>
          <td>${barber.phone || "-"}</td>
          <td>${barber.user_username || "-"}</td>
          <td>${barber.is_active ? "Activo" : "Inactivo"}</td>
        </tr>
      `).join("");

    pageContent.innerHTML = `
      <div class="panel">
        <div class="panel-header"><h3>Barberos</h3></div>
        <div class="table-wrapper">
          <table class="table-block">
            <thead>
              <tr>
                <th>ID</th>
                <th>Nombre</th>
                <th>Alias</th>
                <th>Teléfono</th>
                <th>Usuario</th>
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
    showPageError(error.message || "No se pudo cargar los barberos.");
  }
}

window.loadBarbers = loadBarbers;
