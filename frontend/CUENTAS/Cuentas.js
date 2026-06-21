

let debts=[];
let payments=[];

function openModal(){modal.classList.add("active");}
function closeModal(){modal.classList.remove("active");}

function saveDebt(){

    debts.push({
        client:client.value,
        concept:concept.value,
        amount:parseFloat(amount.value),
        paid:0,
        date:date.value
    });

    closeModal();
    render();
}

function addPayment(i){

    let val=parseFloat(prompt("Monto del abono:"));
    if(!val) return;

    debts[i].paid += val;

    payments.push({
        client:debts[i].client,
        amount:val,
        date:new Date().toLocaleDateString()
    });

    render();
}

function status(d){

    if(d.paid>=d.amount) return "paid";
    if(d.paid>0) return "partial";

    let today=new Date();
    let due=new Date(d.date);

    if(today>due) return "late";

    return "pending";
}

function render(){

    let grid=document.getElementById("grid");
    grid.innerHTML="";

    debts.forEach((d,i)=>{

        let st=status(d);
        let remaining=d.amount-d.paid;

        let alert="";

        if(st==="late"){
            alert=`<div class="alert">⚠ Deuda vencida</div>`;
        }

        grid.innerHTML+=`
        <div class="card">

            <div class="title">${d.client}</div>
            <div class="meta">${d.concept}</div>
            <div class="meta">Total: $${d.amount}</div>
            <div class="meta">Pagado: $${d.paid}</div>
            <div class="meta">Saldo: $${remaining}</div>

            <span class="badge ${st}">
                ${st.toUpperCase()}
            </span>

            ${alert}

            <div style="margin-top:10px;display:flex;gap:8px;">
                <button class="secondary" onclick="addPayment(${i})">Abonar</button>
            </div>

        </div>`;
    });

    let h=document.getElementById("history");
    h.innerHTML="";

    payments.forEach(p=>{
        h.innerHTML+=`
        <tr>
            <td>${p.client}</td>
            <td>$${p.amount}</td>
            <td>${p.date}</td>
        </tr>`;
    });
}

/* EXPORT CSV SIMPLE */
function exportData(){

    let csv="Cliente,Monto,Pagado,Concepto\n";

    debts.forEach(d=>{
        csv+=`${d.client},${d.amount},${d.paid},${d.concept}\n`;
    });

    let blob=new Blob([csv],{type:"text/csv"});
    let a=document.createElement("a");

    a.href=URL.createObjectURL(blob);
    a.download="cuentas_por_cobrar.csv";
    a.click();
}

render();
