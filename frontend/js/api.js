const API_BASE_URL = (() => {
  if (typeof window !== "undefined" && window.location && window.location.origin && window.location.origin !== "null") {
    return window.location.origin;
  }
  return "http://127.0.0.1:8000";
})();

function buildUrl(endpoint) {
  if (endpoint.startsWith("http://") || endpoint.startsWith("https://")) {
    return endpoint;
  }
  return `${API_BASE_URL}${endpoint.startsWith("/") ? "" : "/"}${endpoint}`;
}

function getAuthToken() {
  return localStorage.getItem("magnus_token");
}

function setAuthToken(token) {
  localStorage.setItem("magnus_token", token);
}

function clearAuthToken() {
  localStorage.removeItem("magnus_token");
  localStorage.removeItem("magnus_username");
  localStorage.removeItem("magnus_full_name");
  localStorage.removeItem("magnus_role");
}

function getAuthUser() {
  return {
    username: localStorage.getItem("magnus_username") || "",
    full_name: localStorage.getItem("magnus_full_name") || "",
    role: localStorage.getItem("magnus_role") || ""
  };
}

function setAuthUser(user) {
  if (!user) return;
  if (user.username) {
    localStorage.setItem("magnus_username", user.username);
  }
  if (user.full_name) {
    localStorage.setItem("magnus_full_name", user.full_name);
  }
  if (user.role) {
    localStorage.setItem("magnus_role", user.role);
  }
}

async function apiRequest(endpoint, options = {}) {
  const token = getAuthToken();
  const headers = {
    Accept: "application/json",
    ...(options.headers || {})
  };

  if (options.body && typeof options.body !== "string") {
    headers["Content-Type"] = "application/json";
    options.body = JSON.stringify(options.body);
  }

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const response = await fetch(buildUrl(endpoint), {
    credentials: "same-origin",
    ...options,
    headers
  });

  const contentType = response.headers.get("content-type") || "";
  const isJson = contentType.includes("application/json");
  const data = isJson ? await response.json().catch(() => null) : null;

  if (!response.ok) {
    let message = "Ocurrió un error en el servidor.";
    if (data && data.detail) {
      // detail puede ser objeto estructurado (ej. account_locked) — no usarlo como texto
      message = typeof data.detail === "string" ? data.detail : "Error en el servidor.";
    } else if (data && data.message) {
      message = data.message;
    } else if (response.status === 401) {
      message = "No autorizado. Por favor inicie sesión nuevamente.";
    } else if (response.status === 403) {
      message = "Acceso denegado.";
    } else if (response.status === 400) {
      message = "Solicitud inválida.";
    }

    if (response.status === 401) {
      clearAuthToken();
      // No redirigir si ya estamos en la página de login (evita recargar y borrar el mensaje)
      if (!window.location.pathname.includes("/LOGIN/")) {
        window.location.replace("/LOGIN/login.html");
      }
    }
    if (response.status === 403) {
      clearAuthToken();
      if (window.onAuthError) {
        window.onAuthError(message);
      }
    }

    const err = new Error(message);
    err.responseData = data;  // datos crudos para que el llamador pueda inspeccionarlos
    throw err;
  }

  return data;
}

window.api = {
  apiRequest,
  getAuthToken,
  setAuthToken,
  clearAuthToken,
  getAuthUser,
  setAuthUser,
  buildUrl
};
window.apiRequest = apiRequest;
