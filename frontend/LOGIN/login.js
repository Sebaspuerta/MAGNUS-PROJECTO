// ── MODAL RECUPERAR CONTRASEÑA ──────────────────────────────────

function openRecoverModal() {
    document.getElementById("modal-recover").classList.add("visible");
    document.getElementById("rec-username").value = "";
    document.getElementById("rec-msg").textContent = "";
    document.getElementById("rec-msg").className = "";
    document.getElementById("rec-result").textContent = "";
    document.getElementById("rec-result").style.display = "none";
    document.getElementById("rec-form-area").style.display = "";
    document.getElementById("rec-submit").disabled = false;
    document.getElementById("rec-username").focus();
}

function closeRecoverModal() {
    document.getElementById("modal-recover").classList.remove("visible");
}

document.addEventListener("DOMContentLoaded", () => {

    // Enlace "¿Olvidaste tu contraseña?" → abre modal
    const linkRecover = document.getElementById("link-recover");
    if (linkRecover) {
        linkRecover.addEventListener("click", function (e) {
            e.preventDefault();
            openRecoverModal();
        });
    }

    // Cierre del modal al hacer clic en el overlay o en el enlace de cancelar
    const overlay = document.getElementById("modal-recover");
    if (overlay) {
        overlay.addEventListener("click", function (e) {
            if (e.target === overlay) closeRecoverModal();
        });
    }
    const cancelLink = document.getElementById("rec-cancel");
    if (cancelLink) {
        cancelLink.addEventListener("click", function (e) {
            e.preventDefault();
            closeRecoverModal();
        });
    }

    // Botón de recuperar contraseña
    const recSubmit = document.getElementById("rec-submit");
    if (recSubmit) {
        recSubmit.addEventListener("click", async function () {
            const username = document.getElementById("rec-username").value.trim();
            const msgEl   = document.getElementById("rec-msg");

            msgEl.className = "";
            msgEl.textContent = "";

            if (!username) {
                msgEl.textContent = "Escribe tu nombre de usuario.";
                return;
            }

            recSubmit.disabled = true;
            msgEl.textContent = "Verificando...";

            try {
                const data = await window.api.apiRequest(
                    "/api/security/user-role-hint?username=" + encodeURIComponent(username)
                );

                msgEl.textContent = "";

                var mensaje;
                if (data.hint === "admin") {
                    var nombre = (data.display_name || "Administrador").toUpperCase();
                    mensaje = "HOLA " + nombre + ", TE RECORDAMOS QUE ERES EL ADMINISTRADOR. "
                            + "NO TE RECOMENDAMOS CAMBIAR TUS CREDENCIALES. "
                            + "SI SE TE OLVIDÓ TU CONTRASEÑA, PONTE EN CONTACTO CON LOS DESARROLLADORES.";
                } else {
                    mensaje = "PONTE EN CONTACTO CON UN SUPERIOR, ADMINISTRADOR O LOS DESARROLLADORES.";
                }

                var resultEl = document.getElementById("rec-result");
                resultEl.textContent = mensaje;
                resultEl.style.display = "block";
                document.getElementById("rec-form-area").style.display = "none";

            } catch (err) {
                recSubmit.disabled = false;
                msgEl.textContent = "Error al procesar la solicitud. Inténtalo de nuevo.";
            }
        });
    }

    const inputs = document.querySelectorAll("input");
    inputs.forEach(input => {
        input.addEventListener("focus", () => {
            input.parentElement.style.transform = "scale(1.02)";
        });
        input.addEventListener("blur", () => {
            input.parentElement.style.transform = "scale(1)";
        });
    });

    if (window.api && window.api.getAuthToken()) {
        window.location.replace("/DASHBOARD/Dashboard.html");
        return;
    }

    const params = new URLSearchParams(window.location.search);
    if (params.get("expired") === "1") {
        document.getElementById("error-msg").textContent =
            "Tu sesión se cerró por inactividad. Inicia sesión de nuevo.";
    }

    const form = document.getElementById("login-form");
    const errorMsg = document.getElementById("error-msg");
    const btnSubmit = document.getElementById("btn-submit");

    form.addEventListener("submit", async (e) => {
        e.preventDefault();

        const username = document.getElementById("username").value.trim();
        const password = document.getElementById("password").value;

        if (!username || !password) {
            errorMsg.textContent = "Ingresa usuario y contraseña.";
            return;
        }

        btnSubmit.disabled = true;
        btnSubmit.textContent = "Verificando...";
        errorMsg.textContent = "";

        try {
            const data = await window.api.apiRequest("/api/security/login", {
                method: "POST",
                body: { username, password }
            });

            window.api.setAuthToken(data.access_token);
            window.api.setAuthUser({
                username: data.username,
                full_name: data.full_name,
                role: data.role
            });

            window.location.href = "/DASHBOARD/Dashboard.html";

        } catch (err) {
            const detail = err.responseData && err.responseData.detail;
            if (detail && typeof detail === "object" && detail.code === "account_locked") {
                const min = detail.minutes_remaining;
                const mensajes = [
                    "¡Uy! Demasiados intentos. Tómate un café y vuelve en {min} minutos.",
                    "Calma, vaquero. La cuenta está bloqueada. Inténtalo de nuevo en {min} minutos.",
                    "5 intentos fallidos... ¿seguro que es tu clave? Vuelve en {min} minutos.",
                    "Sistema bloqueado por seguridad. Respira hondo y regresa en {min} minutos.",
                    "Demasiados intentos. El sistema necesita un respiro. Vuelve en {min} minutos.",
                    "¡Alto ahí! Por seguridad, espera {min} minutos antes de volver a intentar."
                ];
                const elegido = mensajes[Math.floor(Math.random() * mensajes.length)];
                errorMsg.textContent = elegido.replace("{min}", min);
            } else {
                errorMsg.textContent = err.message || "Error al iniciar sesión.";
            }
            btnSubmit.disabled = false;
            btnSubmit.textContent = "Entrar";
        }
    });

});
