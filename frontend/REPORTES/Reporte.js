'use strict';

var _cache = null; /* { range, barbers } — evita llamadas API al filtrar por barbero */

function toISO(d) {
    return d.toISOString().slice(0, 10);
}

/* Convierte el selector "day/week/month" a fechas ISO que el backend entiende */
function getDateRange() {
    var today = new Date();
    var range = document.getElementById('range').value;
    var end   = toISO(today);
    var start;
    if (range === 'day') {
        start = end;
    } else if (range === 'week') {
        var w = new Date(today); w.setDate(w.getDate() - 6);
        start = toISO(w);
    } else { /* month */
        var m = new Date(today); m.setDate(m.getDate() - 29);
        start = toISO(m);
    }
    return { range: range, start_date: start, end_date: end };
}

function fmt(n) {
    return Number(n).toLocaleString('es-CO', { minimumFractionDigits: 0, maximumFractionDigits: 0 });
}

/* Actualiza el select de barberos con los datos reales preservando la selección actual */
function populateBarberSelect(barbers) {
    var sel  = document.getElementById('barber');
    var prev = sel.value;
    sel.innerHTML = '<option value="all">Todos los barberos</option>';
    barbers.forEach(function (b) {
        var opt = document.createElement('option');
        opt.value       = b.barber_name;
        opt.textContent = b.barber_name;
        sel.appendChild(opt);
    });
    if (Array.from(sel.options).some(function (o) { return o.value === prev; })) {
        sel.value = prev;
    }
}

/* Filtra, totaliza y pinta la tabla de barberos + KPIs de ventas/servicios/comisiones */
function renderTable(barbers) {
    var filter   = document.getElementById('barber').value;
    var rows     = filter === 'all' ? barbers : barbers.filter(function (b) { return b.barber_name === filter; });
    var totalSales = 0, totalSvc = 0, totalComm = 0;
    var tbody    = document.getElementById('table');
    tbody.innerHTML = '';

    if (rows.length === 0) {
        tbody.innerHTML = '<tr><td colspan="4" style="text-align:center;color:var(--muted);padding:20px;">Sin datos para este barbero en el período seleccionado.</td></tr>';
    } else {
        rows.forEach(function (b) {
            totalSales += b.sales_total;
            totalSvc   += b.orders_count;
            totalComm  += b.estimated_commission;
            tbody.innerHTML += [
                '<tr>',
                '<td>' + b.barber_name + '</td>',
                '<td>' + b.orders_count + '</td>',
                '<td>$' + fmt(b.sales_total) + '</td>',
                '<td>$' + fmt(b.estimated_commission) + '</td>',
                '</tr>'
            ].join('');
        });
    }

    document.getElementById('sales').textContent       = '$' + fmt(totalSales);
    document.getElementById('services').textContent    = totalSvc;
    document.getElementById('commissions').textContent = '$' + fmt(totalComm);
}

/* Pinta los recuadros de productos más/menos vendidos */
function renderProducts(products) {
    var cards = document.querySelectorAll('.grid .card');
    if (!cards.length) return;

    var topText = products.slice(0, 3)
        .map(function (p) { return p.product_name + ' (' + p.quantity_sold + ')'; })
        .join(', ') || 'Sin productos vendidos en este período.';

    var bottomText = products.length > 3
        ? products.slice(-3).map(function (p) { return p.product_name + ' (' + p.quantity_sold + ')'; }).join(', ')
        : 'No hay suficientes datos para comparar.';

    if (cards[0]) cards[0].querySelector('.meta').textContent = topText;
    if (cards[1]) cards[1].querySelector('.meta').textContent = bottomText;
    /* cards[2] (Inventario general) se deja estático */
}

/* Llamado por onchange="render()" en ambos selectores del HTML */
async function render() {
    var dr = getDateRange();

    /* Si solo cambió el barbero (mismo rango en caché) → filtrado local, sin llamadas API */
    if (_cache && _cache.range === dr.range) {
        renderTable(_cache.barbers);
        return;
    }

    var qs = '?start_date=' + dr.start_date + '&end_date=' + dr.end_date;

    try {
        var results = await Promise.all([
            window.api.apiRequest('/api/reports/sales-by-barber' + qs),
            window.api.apiRequest('/api/reports/top-products'    + qs + '&limit=10'),
            window.api.apiRequest('/api/reports/accounts-receivable')
        ]);

        var byBarber  = results[0];
        var topProds  = results[1];
        var arReport  = results[2];

        _cache = { range: dr.range, barbers: byBarber.barbers };

        populateBarberSelect(byBarber.barbers);
        renderTable(byBarber.barbers);
        renderProducts(topProds.products);

        document.getElementById('debts').textContent = '$' + fmt(arReport.total_balance);

    } catch (e) {
        document.getElementById('table').innerHTML =
            '<tr><td colspan="4" style="color:var(--red-2);text-align:center;padding:20px;">' +
            (e.message || 'Error al cargar reportes.') + '</td></tr>';
    }
}

/* EXPORT / PRINT — sin tocar */
function printReport() {
    window.print();
}

document.addEventListener('DOMContentLoaded', render);
