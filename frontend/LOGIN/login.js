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
            errorMsg.textContent = err.message || "Error al iniciar sesión.";
            btnSubmit.disabled = false;
            btnSubmit.textContent = "Entrar";
        }
    });

});
