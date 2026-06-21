let services = [];

function openModal(i=null){
    document.getElementById('modal').classList.add('active');

    if(i!==null){
        let s = services[i];
        document.getElementById('index').value=i;
        document.getElementById('name').value=s.name;
        document.getElementById('desc').value=s.desc;
        document.getElementById('price').value=s.price;
        document.getElementById('duration').value=s.duration;
        document.getElementById('category').value=s.category;
        document.getElementById('consumables').value=s.consumables.join(", ");
    } else clear();
}

function closeModal(){
    document.getElementById('modal').classList.remove('active');
}

function clear(){
    document.getElementById('index').value="";
    document.getElementById('name').value="";
    document.getElementById('desc').value="";
    document.getElementById('price').value="";
    document.getElementById('duration').value="";
    document.getElementById('consumables').value="";
}

function save(){
    let i=document.getElementById('index').value;

    let obj={
        name:name.value,
        desc:desc.value,
        price:price.value,
        duration:duration.value,
        category:category.value,
        consumables:consumables.value.split(",").map(x=>x.trim()),
        active:true
    };

    i===""?services.push(obj):services[i]=obj;

    closeModal();
    render();
}

function toggle(i){
    services[i].active=!services[i].active;
    render();
}

function remove(i){
    services.splice(i,1);
    render();
}

function render(){
    let g=document.getElementById('grid');
    let q=document.getElementById('search').value.toLowerCase();

    g.innerHTML="";

    services.filter(s=>s.name.toLowerCase().includes(q))
    .forEach((s,i)=>{
        g.innerHTML+=`
        <div class="card">
            <h3>${s.name}</h3>
            <div class="meta">${s.category}</div>
            <div class="meta">${s.desc}</div>
            <div class="meta">💰 $${s.price} | ⏱ ${s.duration} min</div>
            <div class="meta">🧴 ${s.consumables.join(", ")}</div>

            <span class="badge ${s.active?'active':'inactive'}">
                ${s.active?'Activo':'Inactivo'}
            </span>

            <div class="actions">
                <button class="secondary" onclick="openModal(${i})">Editar</button>
                <button class="secondary" onclick="toggle(${i})">Toggle</button>
                <button class="danger" onclick="remove(${i})">Eliminar</button>
            </div>
        </div>`;
    });
}

render();