
let open = false;
let sales = 0;
let expenses = 0;
let log = [];

function openCash(){
    open = true;
    document.getElementById("status").innerText="ABIERTA";
    document.getElementById("status").className="badge open";
}

function addSale(){

    if(!open) return alert("Abre la caja primero");

    let amount = parseFloat(document.getElementById("amount").value);
    let method = document.getElementById("method").value;
    let concept = document.getElementById("concept").value;

    sales += amount;

    log.push({
        type:"Venta",
        amount,
        method
    });

    render();
}

function addExpense(){

    if(!open) return alert("Abre la caja primero");

    let amount = parseFloat(document.getElementById("amount").value);
    let concept = document.getElementById("concept").value;

    expenses += amount;

    log.push({
        type:"Egreso",
        amount,
        method:"Gasto"
    });

    render();
}

function closeCash(){

    if(!open) return;

    let balance = sales - expenses;

    alert("CIERRE DE CAJA\nTotal: "+balance);

    open = false;
    document.getElementById("status").innerText="CERRADA";
    document.getElementById("status").className="badge closed";

    log = [];
    sales = 0;
    expenses = 0;

    render();
}

function render(){

    document.getElementById("ventas").innerText = sales;
    document.getElementById("egresos").innerText = expenses;
    document.getElementById("balance").innerText = sales - expenses;

    let t=document.getElementById("log");
    t.innerHTML="";

    log.forEach(l=>{
        t.innerHTML+=`
        <tr>
            <td>${l.type}</td>
            <td>$${l.amount}</td>
            <td>${l.method}</td>
        </tr>`;
    });
}

render();
