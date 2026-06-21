let products=[];
let history=[];

function openModal(){
    document.getElementById("modal").classList.add("active");
}

function closeModal(){
    document.getElementById("modal").classList.remove("active");
}

function save(){

    let p={
        name:name.value,
        type:type.value,
        stock:parseInt(stock.value),
        min:parseInt(min.value),
        price:parseFloat(price.value),
        expiry:expiry.value,
        active:true
    };

    products.push(p);

    history.push({
        name:p.name,
        type:"Entrada",
        qty:p.stock,
        reason:"Registro inicial"
    });

    closeModal();
    render();
}

function consume(index,qty,reason){
    products[index].stock -= qty;

    history.push({
        name:products[index].name,
        type:"Salida",
        qty,
        reason
    });

    render();
}

function adjust(index){

    let qty=parseInt(prompt("Ajuste (+/-):"));
    let reason=prompt("Motivo obligatorio:");

    if(!reason) return;

    products[index].stock += qty;

    history.push({
        name:products[index].name,
        type:"Ajuste",
        qty,
        reason
    });

    render();
}

function render(){

    let grid=document.getElementById("grid");
    grid.innerHTML="";

    products.forEach((p,i)=>{

        let badge="good";
        if(p.stock<=p.min) badge="low";

        let expAlert="";
        if(p.type==="Perecedero" && p.expiry){
            let days=(new Date(p.expiry)-new Date())/86400000;
            if(days<5) expAlert=`<div class="alert">⚠ Vence en ${Math.round(days)} días</div>`;
        }

        grid.innerHTML+=`
        <div class="card">
            <div class="title">${p.name}</div>
            <div class="meta">${p.type}</div>
            <div class="meta">Stock: ${p.stock}</div>
            <div class="meta">Mín: ${p.min}</div>

            <span class="badge ${badge}">
                ${badge==="good"?"OK":"BAJO"}
            </span>

            ${expAlert}

            <div style="margin-top:10px;display:flex;gap:8px;">
                <button class="secondary" onclick="adjust(${i})">Ajuste</button>
                <button class="danger" onclick="consume(${i},1,'Venta simulada')">-1</button>
            </div>
        </div>`;
    });

    let h=document.getElementById("history");
    h.innerHTML="";

    history.forEach(x=>{
        h.innerHTML+=`
        <tr>
            <td>${x.name}</td>
            <td>${x.type}</td>
            <td>${x.qty}</td>
            <td>${x.reason}</td>
        </tr>`;
    });
}

render();
