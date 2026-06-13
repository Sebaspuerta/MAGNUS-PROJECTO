(function () {
  'use strict';

  // ── Estado del módulo ────────────────────────────────────────────────────
  var _clients      = [];
  var _barbers      = [];
  var _services     = [];
  var _products     = [];
  var _currentOrder = null;   // comanda abierta en el detalle

  // ── Helpers de formato ───────────────────────────────────────────────────

  function _fmt(amount) {
    return '$' + Number(amount || 0).toLocaleString('es-CO');
  }

  function _fmtDate(dt) {
    if (!dt) return '—';
    return new Date(dt).toLocaleString('es-CO');
  }

  function _clientName(id) {
    if (!id) return '— Pasante —';
    var c = _clients.find(function (x) { return x.id === id; });
    return c ? c.full_name : 'Cliente #' + id;
  }

  function _barberName(id) {
    if (!id) return '—';
    var b = _barbers.find(function (x) { return x.id === id; });
    return b ? (b.full_name || b.alias || ('Barbero #' + id)) : 'Barbero #' + id;
  }

  function _statusBadge(status) {
    var map = {
      abierta: 'badge-abierta',
      pendiente: 'badge-pendiente',
      cerrada: 'badge-cerrada',
      cancelada: 'badge-cancelada'
    };
    return '<span class="order-badge ' + (map[status] || '') + '">' + (status || '—') + '</span>';
  }

  function _payBadge(status) {
    var map = {
      pendiente: 'badge-pendiente',
      pagado: 'badge-pagado',
      fiado: 'badge-fiado',
      parcial: 'badge-parcial'
    };
    return '<span class="order-badge ' + (map[status] || '') + '">' + (status || '—') + '</span>';
  }

  function _removeModal(id) {
    var el = document.getElementById(id);
    if (el) el.remove();
  }

  function _pc() {
    return document.getElementById('page-content');
  }

  // ── Catálogos ────────────────────────────────────────────────────────────

  async function _loadCatalogs() {
    var results = await Promise.allSettled([
      window.api.apiRequest('/api/clients'),
      window.api.apiRequest('/api/barbers'),
      window.api.apiRequest('/api/services'),
      window.api.apiRequest('/api/inventory/products')
    ]);
    _clients  = results[0].status === 'fulfilled' ? results[0].value : [];
    _barbers  = results[1].status === 'fulfilled' ? results[1].value : [];
    _services = results[2].status === 'fulfilled' ? results[2].value : [];
    _products = results[3].status === 'fulfilled' ? results[3].value : [];
  }

  // ── VISTA: Lista de comandas ──────────────────────────────────────────────

  async function loadOrders() {
    var pc = _pc();
    if (!pc) return;
    pc.innerHTML = '<div class="panel"><div class="panel-header"><h3>Cargando comandas...</h3></div></div>';

    try {
      await _loadCatalogs();
      var orders = await window.api.apiRequest('/api/orders');

      var rows = orders.length === 0
        ? '<tr><td colspan="8" style="text-align:center;padding:24px;color:#8f9baa;">No hay comandas registradas.</td></tr>'
        : orders.slice().reverse().map(function (o) {
            return (
              '<tr>' +
              '<td style="font-weight:700;">#' + o.id + '</td>' +
              '<td>' + _clientName(o.client_id) + '</td>' +
              '<td>' + _barberName(o.barber_id) + '</td>' +
              '<td>' + _statusBadge(o.status) + '</td>' +
              '<td>' + _payBadge(o.payment_status) + '</td>' +
              '<td style="font-weight:700;color:#d9a441;">' + _fmt(o.total) + '</td>' +
              '<td style="font-size:13px;color:#8f9baa;">' + _fmtDate(o.created_at) + '</td>' +
              '<td><button class="btn-action btn-ghost" style="padding:6px 14px;font-size:13px;" ' +
                'onclick="window._orderDetail(' + o.id + ')">Gestionar</button></td>' +
              '</tr>'
            );
          }).join('');

      pc.innerHTML =
        '<div class="panel">' +
          '<div class="panel-header">' +
            '<h3><i class="fa-solid fa-receipt" style="color:#d9a441;margin-right:8px;"></i>Comandas</h3>' +
            '<button class="btn-main" onclick="window._newOrderModal()">+ Nueva Comanda</button>' +
          '</div>' +
          '<div class="table-wrapper">' +
            '<table class="table-block">' +
              '<thead><tr>' +
                '<th>#</th><th>Cliente</th><th>Barbero</th>' +
                '<th>Estado</th><th>Pago</th><th>Total</th>' +
                '<th>Creada</th><th>Acciones</th>' +
              '</tr></thead>' +
              '<tbody>' + rows + '</tbody>' +
            '</table>' +
          '</div>' +
        '</div>';
    } catch (err) {
      showPageError(err.message || 'No se pudieron cargar las comandas.');
    }
  }

  // ── MODAL: Nueva comanda ──────────────────────────────────────────────────

  function _newOrderModal() {
    _removeModal('new-order-modal');

    var clientOptions = '<option value="">— Sin cliente / Pasante —</option>' +
      _clients.filter(function (c) { return c.is_active !== false; }).map(function (c) {
        return '<option value="' + c.id + '">' + c.full_name +
          (c.phone ? ' · ' + c.phone : '') + '</option>';
      }).join('');

    var barberOptions = '<option value="">— Asignar al cerrar —</option>' +
      _barbers.filter(function (b) { return b.is_active !== false; }).map(function (b) {
        return '<option value="' + b.id + '">' + (b.full_name || b.alias) + '</option>';
      }).join('');

    var overlay = document.createElement('div');
    overlay.id = 'new-order-modal';
    overlay.className = 'modal-overlay';
    overlay.innerHTML =
      '<div class="modal-box" style="width:min(500px,95vw);">' +
        '<div class="modal-title-row">' +
          '<h2><i class="fa-solid fa-receipt" style="color:#d9a441;margin-right:8px;"></i>Nueva Comanda</h2>' +
          '<button class="modal-close-x" onclick="document.getElementById(\'new-order-modal\').remove()">&#10005;</button>' +
        '</div>' +
        '<div class="modal-field">' +
          '<label>Cliente <span style="color:#8f9baa;">(opcional)</span></label>' +
          '<select id="nom-client">' + clientOptions + '</select>' +
        '</div>' +
        '<div class="modal-field">' +
          '<label>Barbero <span style="color:#8f9baa;">(puede asignarse al cerrar)</span></label>' +
          '<select id="nom-barber">' + barberOptions + '</select>' +
        '</div>' +
        '<div class="modal-field" style="flex-direction:row;align-items:center;gap:12px;margin-bottom:12px;">' +
          '<input type="checkbox" id="nom-fiado" style="width:18px;height:18px;accent-color:#d9a441;flex-shrink:0;">' +
          '<label for="nom-fiado" style="font-size:14px;color:#c7d0db;cursor:pointer;margin:0;">' +
            'Marcar como fiado (saldo queda en Cuentas por Cobrar)</label>' +
        '</div>' +
        '<div class="modal-field">' +
          '<label>Notas</label>' +
          '<input type="text" id="nom-notes" placeholder="Observaciones opcionales...">' +
        '</div>' +
        '<div id="nom-error" class="login-error" style="display:none;"></div>' +
        '<button class="modal-btn" onclick="window._submitNewOrder()">Crear Comanda</button>' +
      '</div>';

    document.body.appendChild(overlay);
    overlay.addEventListener('click', function (e) { if (e.target === overlay) overlay.remove(); });
  }

  async function _submitNewOrder() {
    var errBox = document.getElementById('nom-error');
    errBox.style.display = 'none';

    var clientVal = document.getElementById('nom-client').value;
    var barberVal = document.getElementById('nom-barber').value;
    var isFiado   = document.getElementById('nom-fiado').checked;
    var notes     = document.getElementById('nom-notes').value.trim();

    var payload = { is_fiado: isFiado, notes: notes || null };
    if (clientVal) payload.client_id = parseInt(clientVal, 10);
    if (barberVal) payload.barber_id = parseInt(barberVal, 10);

    try {
      var order = await window.api.apiRequest('/api/orders', { method: 'POST', body: payload });
      _removeModal('new-order-modal');
      await _openOrderDetail(order.id);
    } catch (err) {
      errBox.textContent = err.message || 'No se pudo crear la comanda.';
      errBox.style.display = 'block';
    }
  }

  // ── VISTA: Detalle de comanda ─────────────────────────────────────────────

  async function _openOrderDetail(orderId) {
    var pc = _pc();
    if (!pc) return;
    pc.innerHTML = '<div class="panel"><div class="panel-header"><h3>Cargando comanda #' + orderId + '...</h3></div></div>';

    try {
      if (!_barbers.length) await _loadCatalogs();
      var order = await window.api.apiRequest('/api/orders/' + orderId);
      _renderOrderDetail(order);
    } catch (err) {
      showPageError(err.message || 'No se pudo cargar la comanda.');
    }
  }

  function _renderOrderDetail(order) {
    _currentOrder = order;
    var pc = _pc();
    if (!pc) return;

    var canEdit = order.status === 'abierta' || order.status === 'pendiente';

    // ── Info grid ──
    var infoFields = [
      { l: 'Comanda',    v: '#' + order.id },
      { l: 'Estado',     v: _statusBadge(order.status) },
      { l: 'Pago',       v: _payBadge(order.payment_status) },
      { l: 'Cliente',    v: _clientName(order.client_id) },
      { l: 'Barbero',    v: _barberName(order.barber_id) },
      { l: 'Fiado',      v: order.is_fiado
          ? '<span style="color:#ffc861;font-weight:700;">Sí</span>'
          : '<span style="color:#8f9baa;">No</span>' },
      { l: 'Subtotal',   v: _fmt(order.subtotal) },
      { l: 'Descuento',  v: _fmt(order.discount) },
      { l: 'Total',      v: '<span style="color:#d9a441;font-weight:700;">' + _fmt(order.total) + '</span>' },
      { l: 'Abonado',    v: _fmt(order.amount_paid) },
      { l: 'Creada',     v: _fmtDate(order.created_at) },
      { l: 'Cerrada',    v: _fmtDate(order.closed_at) }
    ];
    var infoHtml = infoFields.map(function (f) {
      return '<div class="order-detail-field"><label>' + f.l + '</label><span>' + f.v + '</span></div>';
    }).join('');

    // ── Tabla de ítems ──
    var itemRows = !order.items || order.items.length === 0
      ? '<tr><td colspan="6" style="text-align:center;color:#8f9baa;padding:20px;">' +
          'Sin ítems. Agrega servicios o productos usando el formulario de abajo.</td></tr>'
      : order.items.map(function (item) {
          var typeBadge = item.item_type === 'servicio'
            ? '<span class="order-badge badge-abierta">Servicio</span>'
            : '<span class="order-badge badge-parcial">Producto</span>';
          var delBtn = canEdit
            ? '<button class="btn-action btn-cancel" style="padding:4px 10px;font-size:12px;" ' +
                'onclick="window._removeItem(' + order.id + ',' + item.id + ')">&#10005;</button>'
            : '<span style="color:#4a5568;">—</span>';
          return (
            '<tr>' +
            '<td>' + typeBadge + '</td>' +
            '<td>' + (item.description || '—') + '</td>' +
            '<td style="text-align:center;">' + item.quantity + '</td>' +
            '<td>' + _fmt(item.unit_price) + '</td>' +
            '<td style="font-weight:700;color:#d9a441;">' + _fmt(item.total_price) + '</td>' +
            '<td>' + delBtn + '</td>' +
            '</tr>'
          );
        }).join('');

    // ── Formulario agregar ítem ──
    var addHtml = '';
    if (canEdit) {
      var svcOpts = _services
        .filter(function (s) { return s.is_active !== false; })
        .map(function (s) {
          return '<option value="' + s.id + '" data-price="' + (s.price || 0) + '">' +
            s.name + ' — ' + _fmt(s.price) + '</option>';
        }).join('');

      var prodOpts = _products
        .filter(function (p) { return p.is_active !== false; })
        .map(function (p) {
          return '<option value="' + p.id + '" data-price="' + (p.sale_price || 0) + '">' +
            p.name + ' (stock: ' + (p.current_stock || 0) + ') — ' + _fmt(p.sale_price) + '</option>';
        }).join('');

      addHtml =
        '<div class="add-item-section">' +
          '<h4><i class="fa-solid fa-plus-circle" style="margin-right:8px;"></i>Agregar ítem a la comanda</h4>' +
          // Servicios
          '<div class="form-row" style="margin-bottom:14px;">' +
            '<div class="form-group" style="flex:3;">' +
              '<label>Servicio</label>' +
              '<select id="add-svc-sel">' +
                '<option value="">— Seleccione un servicio —</option>' + svcOpts +
              '</select>' +
            '</div>' +
            '<div class="form-group" style="flex:0 0 100px;">' +
              '<label>Cantidad</label>' +
              '<input type="number" id="add-svc-qty" value="1" min="1">' +
            '</div>' +
            '<div class="form-group" style="flex:0 0 auto;">' +
              '<label>&nbsp;</label>' +
              '<button class="btn-action btn-success" ' +
                'onclick="window._addItem(' + order.id + ',\'servicio\')">' +
                'Agregar servicio</button>' +
            '</div>' +
          '</div>' +
          // Productos
          '<div class="form-row">' +
            '<div class="form-group" style="flex:3;">' +
              '<label>Producto</label>' +
              '<select id="add-prod-sel">' +
                '<option value="">— Seleccione un producto —</option>' + prodOpts +
              '</select>' +
            '</div>' +
            '<div class="form-group" style="flex:0 0 100px;">' +
              '<label>Cantidad</label>' +
              '<input type="number" id="add-prod-qty" value="1" min="1">' +
            '</div>' +
            '<div class="form-group" style="flex:0 0 auto;">' +
              '<label>&nbsp;</label>' +
              '<button class="btn-action btn-success" ' +
                'onclick="window._addItem(' + order.id + ',\'producto\')">' +
                'Agregar producto</button>' +
            '</div>' +
          '</div>' +
        '</div>';
    }

    // ── Botones de acción ──
    var actionBtns = '';
    if (canEdit) {
      actionBtns =
        '<button class="btn-action" ' +
          'style="background:linear-gradient(180deg,#c51f1f,#891010);color:#fff;" ' +
          'onclick="window._openCloseModal()">' +
          '<i class="fa-solid fa-check-circle" style="margin-right:6px;"></i>Cerrar Comanda' +
        '</button>' +
        '<button class="btn-action btn-cancel" onclick="window._cancelOrder(' + order.id + ')">' +
          '<i class="fa-solid fa-ban" style="margin-right:6px;"></i>Cancelar Comanda' +
        '</button>';
    }

    // ── Render final ──
    pc.innerHTML =
      '<div class="panel">' +
        '<div class="panel-header">' +
          '<h3>' +
            '<button class="btn-action btn-ghost" style="padding:6px 14px;font-size:13px;margin-right:12px;" ' +
              'onclick="window.loadOrders()">&#8592; Volver</button>' +
            'Comanda #' + order.id +
          '</h3>' +
          '<div>' + _statusBadge(order.status) + '&nbsp;&nbsp;' + _payBadge(order.payment_status) + '</div>' +
        '</div>' +

        '<div class="order-detail-header">' + infoHtml + '</div>' +

        '<h4 style="margin-bottom:10px;color:#c7d0db;font-size:15px;">' +
          '<i class="fa-solid fa-list" style="color:#d9a441;margin-right:8px;"></i>Ítems</h4>' +
        '<div class="table-wrapper">' +
          '<table class="table-block">' +
            '<thead><tr>' +
              '<th>Tipo</th><th>Descripción</th>' +
              '<th style="text-align:center;">Cant.</th>' +
              '<th>Precio unit.</th><th>Total</th><th></th>' +
            '</tr></thead>' +
            '<tbody>' + itemRows + '</tbody>' +
          '</table>' +
        '</div>' +

        addHtml +

        '<div class="order-actions">' + actionBtns + '</div>' +
      '</div>';
  }

  // ── Agregar ítem ─────────────────────────────────────────────────────────

  async function _addItem(orderId, itemType) {
    var payload = { item_type: itemType };

    if (itemType === 'servicio') {
      var sel = document.getElementById('add-svc-sel');
      var qty = document.getElementById('add-svc-qty');
      if (!sel || !sel.value) { alert('Seleccione un servicio antes de agregar.'); return; }
      payload.service_id  = parseInt(sel.value, 10);
      payload.quantity    = parseInt(qty ? qty.value : '1', 10) || 1;
      payload.unit_price  = 0;   // el backend lo sobreescribe con service.price
    } else {
      var psel = document.getElementById('add-prod-sel');
      var pqty = document.getElementById('add-prod-qty');
      if (!psel || !psel.value) { alert('Seleccione un producto antes de agregar.'); return; }
      var opt = psel.options[psel.selectedIndex];
      payload.product_id  = parseInt(psel.value, 10);
      payload.quantity    = parseInt(pqty ? pqty.value : '1', 10) || 1;
      payload.unit_price  = parseFloat(opt.dataset.price || '0');
    }

    try {
      var order = await window.api.apiRequest('/api/orders/' + orderId + '/items', {
        method: 'POST',
        body: payload
      });
      _renderOrderDetail(order);
    } catch (err) {
      alert('Error al agregar ítem:\n' + err.message);
    }
  }

  // ── Eliminar ítem ────────────────────────────────────────────────────────

  async function _removeItem(orderId, itemId) {
    if (!confirm('¿Eliminar este ítem de la comanda?')) return;
    try {
      var order = await window.api.apiRequest(
        '/api/orders/' + orderId + '/items/' + itemId,
        { method: 'DELETE' }
      );
      _renderOrderDetail(order);
    } catch (err) {
      alert('Error al eliminar ítem:\n' + err.message);
    }
  }

  // ── MODAL: Cerrar comanda ─────────────────────────────────────────────────

  function _openCloseModal() {
    var order = _currentOrder;
    if (!order) { alert('No hay comanda activa.'); return; }
    _removeModal('close-order-modal');

    var outstanding = (order.total || 0) - (order.amount_paid || 0);

    var barberOpts = '<option value="">— Seleccione barbero *—</option>' +
      _barbers.filter(function (b) { return b.is_active !== false; }).map(function (b) {
        return '<option value="' + b.id + '"' + (order.barber_id === b.id ? ' selected' : '') + '>' +
          (b.full_name || b.alias) + '</option>';
      }).join('');

    var methods = ['efectivo', 'Nequi', 'Daviplata', 'transferencia', 'tarjeta', 'cortesía'];
    var methodOpts = '<option value="">— Seleccione método *—</option>' +
      methods.map(function (m) { return '<option value="' + m + '">' + m + '</option>'; }).join('');

    var paySection = order.is_fiado
      ? '<div class="empty-state" style="margin-bottom:14px;padding:12px;margin-top:0;">' +
          '<i class="fa-solid fa-wallet" style="color:#ffc861;margin-right:8px;"></i>' +
          'Comanda <strong>fiada</strong> &mdash; el saldo de <strong style="color:#ffc861;">' +
          _fmt(outstanding) + '</strong> quedará registrado en <strong>Cuentas por Cobrar</strong>.' +
        '</div>'
      : '<div class="modal-field">' +
          '<label>Método de pago *</label>' +
          '<select id="com-method">' + methodOpts + '</select>' +
        '</div>' +
        '<div class="modal-field">' +
          '<label>Monto a cobrar (COP) *</label>' +
          '<input type="number" id="com-amount" value="' + Math.round(outstanding) +
            '" min="1" style="background:#0b111b;border:1px solid #1f2c39;color:#eef2ff;' +
            'border-radius:12px;padding:14px 16px;width:100%;font-family:Poppins,sans-serif;font-size:14px;">' +
        '</div>';

    var overlay = document.createElement('div');
    overlay.id = 'close-order-modal';
    overlay.className = 'modal-overlay';
    overlay.innerHTML =
      '<div class="modal-box" style="width:min(480px,95vw);">' +
        '<div class="modal-title-row">' +
          '<h2><i class="fa-solid fa-check-circle" style="color:#22c55e;margin-right:8px;"></i>' +
            'Cerrar Comanda #' + order.id + '</h2>' +
          '<button class="modal-close-x" onclick="document.getElementById(\'close-order-modal\').remove()">&#10005;</button>' +
        '</div>' +
        // Resumen financiero
        '<div style="background:#080d13;border:1px solid #1a2633;border-radius:10px;' +
          'padding:14px;margin-bottom:16px;">' +
          '<div style="display:flex;justify-content:space-between;margin-bottom:6px;">' +
            '<span style="color:#8f9baa;">Total comanda</span>' +
            '<strong>' + _fmt(order.total) + '</strong>' +
          '</div>' +
          '<div style="display:flex;justify-content:space-between;margin-bottom:6px;">' +
            '<span style="color:#8f9baa;">Ya abonado</span>' +
            '<span>' + _fmt(order.amount_paid) + '</span>' +
          '</div>' +
          '<div style="display:flex;justify-content:space-between;padding-top:8px;' +
            'border-top:1px solid #1a2633;">' +
            '<span style="color:#d9a441;font-weight:700;">Saldo pendiente</span>' +
            '<strong style="color:#d9a441;">' + _fmt(outstanding) + '</strong>' +
          '</div>' +
        '</div>' +
        '<div class="modal-field">' +
          '<label>Barbero responsable *</label>' +
          '<select id="com-barber">' + barberOpts + '</select>' +
        '</div>' +
        paySection +
        '<div class="modal-field">' +
          '<label>Nota del cierre <span style="color:#8f9baa;">(opcional)</span></label>' +
          '<input type="text" id="com-note" placeholder="Observación...">' +
        '</div>' +
        '<div id="com-error" class="login-error" style="display:none;"></div>' +
        '<button class="modal-btn" onclick="window._submitClose()">' +
          '<i class="fa-solid fa-check" style="margin-right:6px;"></i>Confirmar cierre' +
        '</button>' +
      '</div>';

    document.body.appendChild(overlay);
    overlay.addEventListener('click', function (e) { if (e.target === overlay) overlay.remove(); });
  }

  async function _submitClose() {
    var order  = _currentOrder;
    if (!order) return;

    var errBox   = document.getElementById('com-error');
    var barberEl = document.getElementById('com-barber');
    var noteEl   = document.getElementById('com-note');

    errBox.style.display = 'none';

    if (!barberEl || !barberEl.value) {
      errBox.textContent = 'Debe seleccionar el barbero responsable.';
      errBox.style.display = 'block';
      return;
    }

    var payload = {
      barber_id: parseInt(barberEl.value, 10),
      note: noteEl && noteEl.value.trim() ? noteEl.value.trim() : null
    };

    if (!order.is_fiado) {
      var methodEl = document.getElementById('com-method');
      var amountEl = document.getElementById('com-amount');
      if (!methodEl || !methodEl.value) {
        errBox.textContent = 'Debe seleccionar el método de pago.';
        errBox.style.display = 'block';
        return;
      }
      var amount = parseFloat(amountEl ? amountEl.value : '0');
      if (!amount || amount <= 0) {
        errBox.textContent = 'El monto debe ser mayor que cero.';
        errBox.style.display = 'block';
        return;
      }
      payload.payment_method = methodEl.value;
      payload.payment_amount = amount;
    }

    try {
      var updated = await window.api.apiRequest('/api/orders/' + order.id + '/close', {
        method: 'PATCH',
        body: payload
      });
      _removeModal('close-order-modal');
      _renderOrderDetail(updated);
    } catch (err) {
      errBox.textContent = err.message || 'No se pudo cerrar la comanda.';
      errBox.style.display = 'block';
    }
  }

  // ── Cancelar comanda ──────────────────────────────────────────────────────

  async function _cancelOrder(orderId) {
    if (!confirm('¿Está seguro de cancelar esta comanda?\nEsta acción no se puede deshacer.')) return;
    try {
      var order = await window.api.apiRequest('/api/orders/' + orderId + '/cancel', { method: 'PATCH' });
      _renderOrderDetail(order);
    } catch (err) {
      alert('Error al cancelar la comanda:\n' + err.message);
    }
  }

  // ── Exports globales ──────────────────────────────────────────────────────

  window.loadOrders      = loadOrders;
  window._newOrderModal  = _newOrderModal;
  window._submitNewOrder = _submitNewOrder;
  window._orderDetail    = _openOrderDetail;
  window._addItem        = _addItem;
  window._removeItem     = _removeItem;
  window._openCloseModal = _openCloseModal;
  window._submitClose    = _submitClose;
  window._cancelOrder    = _cancelOrder;

}());
