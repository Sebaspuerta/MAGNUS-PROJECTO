
/* SIMULACIÓN DE DATOS */
let data = [
    {barber:"Ragnar", services:12, sales:240, commission:24},
    {barber:"Loki", services:8, sales:160, commission:16},
    {barber:"Thor", services:15, sales:300, commission:30}
];

function render(){

    let filter=document.getElementById("barber").value;

    let filtered = data.filter(d => filter==="all" || d.barber===filter);

    let totalSales=0, totalServices=0, totalComm=0;

    let tbody=document.getElementById("table");
    tbody.innerHTML="";

    filtered.forEach(d=>{
        totalSales+=d.sales;
        totalServices+=d.services;
        totalComm+=d.commission;

        tbody.innerHTML+=`
        <tr>
            <td>${d.barber}</td>
            <td>${d.services}</td>
            <td>$${d.sales}</td>
            <td>$${d.commission}</td>
        </tr>`;
    });

    document.getElementById("sales").innerText=totalSales;
    document.getElementById("services").innerText=totalServices;
    document.getElementById("commissions").innerText=totalComm;
    document.getElementById("debts").innerText=5;
}

/* EXPORT / PRINT */
function printReport(){
    window.print();
}

render();
