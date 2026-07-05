'use strict';

/* Mapeo alert_type (backend) → presentación visual */
const ALERT_MAP = {
    stock_agotado:       { title: 'Producto agotado',  level: 'red',    action: '/INVENTARIO/Inventario.html' },
    stock_bajo:          { title: 'Stock bajo',         level: 'orange', action: '/INVENTARIO/Inventario.html' },
    producto_por_vencer: { title: 'Por vencer',         level: 'orange', action: '/INVENTARIO/Inventario.html' },
    deuda_vencida:       { title: 'Deuda vencida',      level: 'red',    action: '/CUENTAS/Cuentas.html' },
};

function renderAlerts(alerts) {
    const grid = document.getElementById('grid');

    document.getElementById('deudas').textContent    = alerts.filter(a => a.alert_type === 'deuda_vencida').length;
    document.getElementById('stockBajo').textContent  = alerts.filter(a => a.alert_type === 'stock_bajo').length;
    document.getElementById('agotados').textContent   = alerts.filter(a => a.alert_type === 'stock_agotado').length;
    document.getElementById('comandas').textContent   = alerts.filter(a => a.alert_type === 'comanda_abierta').length;

    if (alerts.length === 0) {
        grid.innerHTML = [
            '<div class="card" style="grid-column:1/-1;text-align:center;cursor:default;">',
            '  <div class="title">Sin alertas activas</div>',
            '  <div class="meta">Todo está en orden por ahora.</div>',
            '</div>'
        ].join('');
        return;
    }

    grid.innerHTML = alerts.map(function (a) {
        var info = ALERT_MAP[a.alert_type] || { title: a.alert_type, level: 'blue', action: '#' };
        return [
            '<div class="card" onclick="window.location.href=\'' + info.action + '\'">',
            '  <div class="title">' + info.title + '</div>',
            '  <div class="meta">' + a.message + '</div>',
            '  <span class="badge ' + info.level + '">' + info.level.toUpperCase() + '</span>',
            '  <div class="meta" style="margin-top:10px;">Toca para ir al módulo</div>',
            '</div>'
        ].join('');
    }).join('');
}

function showError(msg) {
    document.getElementById('grid').innerHTML = [
        '<div class="card" style="grid-column:1/-1;cursor:default;">',
        '  <div class="title" style="color:var(--red-2);">Error al cargar alertas</div>',
        '  <div class="meta">' + msg + '</div>',
        '</div>'
    ].join('');
}

async function load() {
    document.getElementById('grid').innerHTML =
        '<div class="meta" style="padding:20px 0;">Generando alertas del sistema...</div>';

    try {
        await window.api.apiRequest('/api/alerts/generate', { method: 'POST' });
    } catch (_) { /* no-fatal: igual cargamos las existentes */ }

    try {
        var alerts = await window.api.apiRequest('/api/alerts');
        renderAlerts(alerts);
    } catch (e) {
        showError(e.message || 'Error de conexión.');
    }
}

document.addEventListener('DOMContentLoaded', load);
