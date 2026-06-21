let items = [];
let discount = 0;

function addItem(){
    let name = prompt("Nombre del servicio/producto:");
    let price = parseFloat(prompt("Precio:"));
    let qty = parseInt(prompt("Cantidad:"));

    if(!name || !price || !qty) return;

    items.push({name,price,qty});
    render();
}

function render(){
    let container = document.getElementById("items");
    container.innerHTML = "";

    let subtotal = 0;

    items.forEach((i,index)=>{
        subtotal += i.price * i.qty;

        container.innerHTML += `
        <div class="item">
            <div>
                <strong>${i.name}</strong><br>
                <small>$${i.price} x ${i.qty}</small>
            </div>
            <div>
                <button onclick="removeItem(${index})" class="btn danger">X</button>
            </div>
        </div>`;
    });

    let total = subtotal - discount;

    document.getElementById("subtotal").innerText = subtotal;
    document.getElementById("discount").innerText = discount;
    document.getElementById("total").innerText = total;
}

function removeItem(i){
    items.splice(i,1);
    render();
}

function applyDiscount(){
    discount = 10;
    render();
}

function clearOrder(){
    items = [];
    discount = 0;
    render();
}

function closeOrder(){

    let barbero = document.getElementById("barbero").value;
    let cliente = document.getElementById("cliente").value;

    if(!barbero){
        alert("Selecciona un barbero");
        return;
    }

    let paymentType = document.getElementById("paymentType").value;
    let total = parseFloat(document.getElementById("total").innerText);
    let payment = parseFloat(document.getElementById("payment").value || 0);

    let status = "pending";

    if(paymentType === "Completo" && payment >= total){
        status = "paid";
    }
    else if(paymentType === "Parcial"){
        status = "partial";
    }
    else if(paymentType === "Fiado"){
        status = "pending";
    }

    document.getElementById("status").className = "badge " + status;
    document.getElementById("status").innerText = status.toUpperCase();

    alert("Comanda cerrada ✔\nCliente: " + cliente + "\nBarbero: " + barbero + "\nEstado: " + status);

    // Simulación inventario
    console.log("Inventario actualizado (simulado)");

    clearOrder();
}

render();