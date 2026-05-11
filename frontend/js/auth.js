function showLoginModal(message) {
  const modal = document.getElementById("login-modal");
  const errorBox = document.getElementById("login-error");
  if (message) {
    errorBox.textContent = message;
    errorBox.style.display = "block";
  } else {
    errorBox.style.display = "none";
  }
  modal.classList.add("active");
}

function hideLoginModal() {
  const modal = document.getElementById("login-modal");
  const errorBox = document.getElementById("login-error");
  errorBox.style.display = "none";
  modal.classList.remove("active");
}

function renderUserName() {
  const userNameElement = document.getElementById("user-name");
  const user = window.api.getAuthUser();
  if (userNameElement) {
    userNameElement.textContent = user.full_name || user.username || "Administrador";
  }
}

function updateCurrentDate() {
  const dateElement = document.getElementById("current-date");
  if (!dateElement) return;
  const date = new Date();
  const formatter = new Intl.DateTimeFormat("es-CO", {
    day: "2-digit",
    month: "long",
    year: "numeric"
  });
  dateElement.textContent = formatter.format(date);
}

function setActiveMenu(moduleName) {
  document.querySelectorAll(".menu li").forEach((item) => {
    item.classList.toggle("active", item.dataset.module === moduleName);
  });
}

function renderDashboardView() {
  const pageContent = document.getElementById("page-content");
  if (!pageContent) return;
  pageContent.innerHTML = window.initialPageContent || pageContent.innerHTML;
}

function renderModulePlaceholder(title, description) {
  const pageContent = document.getElementById("page-content");
  if (!pageContent) return;

  pageContent.innerHTML = `
    <div class="panel">
      <div class="panel-header"><h3>${title}</h3></div>
      <div class="empty-state">${description}</div>
    </div>
  `;
}

async function loadSecurity() {
  const pageContent = document.getElementById("page-content");
  if (!pageContent) return;

  pageContent.innerHTML = `
    <div class="panel">
      <div class="panel-header"><h3>Cargando seguridad y accesos...</h3></div>
    </div>
  `;

  try {
    const users = await window.api.apiRequest("/api/security/users");
    const rows = users.length === 0
      ? `<tr><td colspan="5">No hay usuarios registrados.</td></tr>`
      : users.map((user) => `
        <tr>
          <td>${user.id}</td>
          <td>${user.username}</td>
          <td>${user.full_name}</td>
          <td>${user.role}</td>
          <td>${user.is_active ? "Activo" : "Inactivo"}</td>
        </tr>
      `).join("");

    pageContent.innerHTML = `
      <div class="panel">
        <div class="panel-header"><h3>Seguridad y Accesos</h3></div>
        <div class="table-wrapper">
          <table class="table-block">
            <thead>
              <tr>
                <th>ID</th>
                <th>Usuario</th>
                <th>Nombre</th>
                <th>Rol</th>
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
    renderModulePlaceholder(
      "Seguridad y Accesos",
      error.message || "No se pudo cargar el módulo de seguridad."
    );
  }
}

function handleMenuClick(event) {
  const menuItem = event.currentTarget;
  const moduleName = menuItem.dataset.module;
  if (!moduleName) return;

  setActiveMenu(moduleName);

  switch (moduleName) {
    case "inventory":
      if (window.loadInventory) {
        window.loadInventory();
      }
      break;
    case "clients":
      if (window.loadClients) {
        window.loadClients();
      }
      break;
    case "barbers":
      if (window.loadBarbers) {
        window.loadBarbers();
      }
      break;
    case "services":
      if (window.loadServices) {
        window.loadServices();
      }
      break;
    case "orders":
      if (window.loadOrders) {
        window.loadOrders();
      }
      break;
    case "security":
      if (window.loadSecurity) {
        window.loadSecurity();
      }
      break;
    case "dashboard":
    case "dashboard2":
      renderDashboardView();
      break;
    case "accounts":
      renderModulePlaceholder(
        "Cuentas por Cobrar",
        "Este módulo está disponible en el backend y se cargará pronto."
      );
      break;
    case "alerts":
      renderModulePlaceholder(
        "Alertas",
        "Este módulo está disponible en el backend y se cargará pronto."
      );
      break;
    case "cash":
      renderModulePlaceholder(
        "Caja y Pagos",
        "Este módulo está disponible en el backend y se cargará pronto."
      );
      break;
    case "reports":
      renderModulePlaceholder(
        "Reportes",
        "Este módulo está disponible en el backend y se cargará pronto."
      );
      break;
    default:
      renderDashboardView();
  }
}

async function loginUser() {
  const usernameInput = document.getElementById("login-username");
  const passwordInput = document.getElementById("login-password");
  const errorBox = document.getElementById("login-error");

  if (!usernameInput || !passwordInput) {
    return;
  }

  const username = usernameInput.value.trim();
  const password = passwordInput.value.trim();

  if (!username || !password) {
    errorBox.textContent = "Debe ingresar usuario y contraseña.";
    errorBox.style.display = "block";
    return;
  }

  try {
    const response = await window.api.apiRequest("/api/security/login", {
      method: "POST",
      body: { username, password }
    });

    window.api.setAuthToken(response.access_token);
    window.api.setAuthUser({
      username: response.username,
      full_name: response.full_name,
      role: response.role
    });

    renderUserName();
    hideLoginModal();
    setActiveMenu("dashboard");
    renderDashboardView();
  } catch (error) {
    errorBox.textContent = error.message || "No se pudo iniciar sesión.";
    errorBox.style.display = "block";
  }
}

async function validateSession() {
  const token = window.api.getAuthToken();
  if (!token) {
    showLoginModal();
    return;
  }

  try {
    const user = await window.api.apiRequest("/api/security/me");
    window.api.setAuthUser(user);
    renderUserName();
    hideLoginModal();
  } catch (error) {
    showLoginModal(error.message);
  }
}

function showPageError(message) {
  const pageContent = document.getElementById("page-content");
  if (!pageContent) return;
  pageContent.innerHTML = `
    <div class="panel">
      <div class="panel-header"><h3>Error</h3></div>
      <div class="empty-state">${message}</div>
    </div>
  `;
}

window.onAuthError = (message) => {
  showLoginModal(message);
};

window.loadSecurity = loadSecurity;

function initializeMenu() {
  document.querySelectorAll(".menu li[data-module]").forEach((item) => {
    item.addEventListener("click", handleMenuClick);
  });
}

function initializeLoginForm() {
  const loginButton = document.getElementById("login-button");
  if (loginButton) {
    loginButton.addEventListener("click", loginUser);
  }

  document.addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
      const modal = document.getElementById("login-modal");
      if (modal && modal.classList.contains("active")) {
        loginUser();
      }
    }
  });
}

function initializeApp() {
  const pageContent = document.getElementById("page-content");
  if (pageContent) {
    window.initialPageContent = pageContent.innerHTML;
  }
  initializeMenu();
  initializeLoginForm();
  updateCurrentDate();
  validateSession();
}

if (document.readyState === "loading") {
  window.addEventListener("DOMContentLoaded", initializeApp);
} else {
  initializeApp();
}
