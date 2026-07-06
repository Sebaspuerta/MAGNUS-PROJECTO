// ── MODAL RECUPERAR CONTRASEÑA ──────────────────────────────────

function openRecoverModal() {
    document.getElementById("modal-recover").classList.add("visible");
    document.getElementById("rec-username").value = "";
    document.getElementById("rec-code").value = "";
    document.getElementById("rec-pw1").value = "";
    document.getElementById("rec-pw2").value = "";
    document.getElementById("rec-msg").textContent = "";
    document.getElementById("rec-msg").className = "";
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
            const username  = document.getElementById("rec-username").value.trim();
            const code      = document.getElementById("rec-code").value;
            const pw1       = document.getElementById("rec-pw1").value;
            const pw2       = document.getElementById("rec-pw2").value;
            const msgEl     = document.getElementById("rec-msg");

            msgEl.className = "";
            msgEl.textContent = "";

            if (!username || !code || !pw1 || !pw2) {
                msgEl.textContent = "Completa todos los campos.";
                return;
            }
            if (pw1 !== pw2) {
                msgEl.textContent = "Las contraseñas no coinciden.";
                return;
            }

            recSubmit.disabled = true;
            msgEl.textContent = "Verificando...";

            try {
                const data = await window.api.apiRequest("/api/security/recover-password", {
                    method: "POST",
                    body: { username, master_code: code, new_password: pw1 }
                });

                msgEl.className = "success";
                msgEl.textContent = data.detail || "Contraseña actualizada. Ya puedes iniciar sesión.";

                setTimeout(closeRecoverModal, 2800);

            } catch (err) {
                recSubmit.disabled = false;
                const detail = err.responseData && err.responseData.detail;
                if (detail && typeof detail === "object" && detail.code === "master_locked") {
                    msgEl.textContent = `Código bloqueado por demasiados intentos. Espera ${detail.minutes_remaining} minuto(s).`;
                } else {
                    msgEl.textContent = (typeof detail === "string" ? detail : null)
                        || err.message
                        || "Error al recuperar contraseña.";
                }
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
