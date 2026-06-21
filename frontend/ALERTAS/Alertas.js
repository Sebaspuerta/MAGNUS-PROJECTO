
/* 🔥 SIMULACIÓN DE DATOS DEL SISTEMA */

let alerts = [
    {
        type:"debt",
        title:"Deudas vencidas",
        desc:"3 clientes con pagos atrasados",
        level:"red",
        action:"cuentas.html"
    },
    {
        type:"stock",
        title:"Stock bajo",
        desc:"Cera para barba y cuchillas",
        level:"orange",
        action:"inventario.html"
    },
    {
        type:"stock0",
        title:"Productos agotados",
        desc:"Aceite de barba premium",
        level:"red",
        action:"inventario.html"
    },
    {
        type:"expiry",
        title:"Productos por vencer",
        desc:"Toallas húmedas (3 días)",
        level:"orange",
        action:"inventario.html"
    },
    {
        type:"orders",
        title:"Comandas abiertas",
        desc:"2 comandas sin cerrar en turno",
        level:"blue",
        action:"comanda.html"
    },
    {
        type:"cash",
        title:"Cierre de caja pendiente",
        desc:"Turno noche sin cerrar",
        level:"red",
        action:"caja.html"
    }
];

/* RESUMEN SIMULADO */
document.getElementById("deudas").innerText = 3;
document.getElementById("stockBajo").innerText = 2;
document.getElementById("agotados").innerText = 1;
document.getElementById("comandas").innerText = 2;

/* RENDER ALERTAS */
function render(){

    let g=document.getElementById("grid");
    g.innerHTML="";

    alerts.forEach(a=>{

        g.innerHTML+=`
        <div class="card" onclick="go('${a.action}')">

            <div class="title">${a.title}</div>

            <div class="meta">${a.desc}</div>

            <span class="badge ${a.level}">
                ${a.level.toUpperCase()}
            </span>

            <div class="meta" style="margin-top:10px;">
                👉 Click para ir al módulo
            </div>

        </div>`;
    });
}

/* REDIRECCIÓN SIMULADA */
function go(page){
    alert("Redirigiendo a: " + page);
    // window.location.href = page;
}

render();

