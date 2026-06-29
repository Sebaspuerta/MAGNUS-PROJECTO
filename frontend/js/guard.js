(function () {
    if (!window.api || !window.api.getAuthToken()) {
        window.location.replace("/LOGIN/login.html");
    }
})();
