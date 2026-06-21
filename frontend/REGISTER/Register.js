document.querySelector("form")
.addEventListener("submit", function(e){

    const pass =
    document.querySelectorAll("input")[3].value;

    const confirm =
    document.querySelectorAll("input")[4].value;

    if(pass !== confirm){

        e.preventDefault();

        alert("Las contraseñas no coinciden");
    }

});