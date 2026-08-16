(function () {
    var INACTIVITY_LIMIT = 3 * 60 * 60 * 1000;
    var ACTIVITY_KEY     = "magnus_last_activity";
    var THROTTLE_MS      = 25 * 1000;

    // Check on page load: if token exists and user has been idle too long, expire session
    if (window.api && window.api.getAuthToken()) {
        var last = parseInt(localStorage.getItem(ACTIVITY_KEY) || "0", 10);
        var now  = Date.now();

        if (last > 0 && (now - last) > INACTIVITY_LIMIT) {
            window.api.clearAuthToken();
            localStorage.removeItem(ACTIVITY_KEY);
            window.location.replace("/LOGIN/login.html?expired=1");
            return;
        }

        localStorage.setItem(ACTIVITY_KEY, String(now));
    }

    // Throttled activity tracker
    var lastUpdate = Date.now();

    function touch() {
        var now = Date.now();
        if (now - lastUpdate < THROTTLE_MS) return;
        lastUpdate = now;
        localStorage.setItem(ACTIVITY_KEY, String(now));
    }

    ["mousemove", "mousedown", "keydown", "scroll", "touchstart", "click"].forEach(function (evt) {
        document.addEventListener(evt, touch, { passive: true });
    });

    // Periodic check every 30 seconds
    setInterval(function () {
        if (!window.api || !window.api.getAuthToken()) return;
        var last = parseInt(localStorage.getItem(ACTIVITY_KEY) || "0", 10);
        if (last > 0 && (Date.now() - last) > INACTIVITY_LIMIT) {
            window.api.clearAuthToken();
            localStorage.removeItem(ACTIVITY_KEY);
            window.location.replace("/LOGIN/login.html?expired=1");
        }
    }, 30 * 1000);

})();
