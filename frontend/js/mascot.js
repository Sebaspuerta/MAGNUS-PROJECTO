(function () {
    'use strict';

    function scheduleNext() {
        var delay = 60000 + Math.random() * 120000;
        setTimeout(showMascot, delay);
    }

    function showMascot() {
        if (document.querySelector('.mascot-corner')) {
            scheduleNext();
            return;
        }

        var corners = ['tl', 'tr', 'bl', 'br'];
        var corner = corners[Math.floor(Math.random() * corners.length)];

        var el = document.createElement('div');
        el.className = 'mascot-corner mascot-' + corner;
        el.innerHTML = '<img src="/img/viking_mascot.png" alt="">';
        document.body.appendChild(el);

        el.addEventListener('animationend', function () {
            el.remove();
            scheduleNext();
        });
    }

    scheduleNext();
})();
