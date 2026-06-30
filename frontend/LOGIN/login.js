document.addEventListener("DOMContentLoaded", () => {

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
