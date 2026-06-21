document.addEventListener("DOMContentLoaded", () => {

    const inputs = document.querySelectorAll("input");

    inputs.forEach(input => {

        input.addEventListener("focus", () => {
            input.parentElement.style.transform = "scale(1.02)";
        });

        input.addEventListener("blur", () => {
            input.parentElement.style.transform = "scale(1)";
        });

    });

});