// FUNCIONES COMUNES

function escapeHtml(value) {

    if (value === null || value === undefined) {
        return "";
    }

    return String(value)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

// PETICIONES A LAS APIs

async function api(url, options = {}) {

    const token = getToken();

    const headers = {
        "Content-Type": "application/json",
        ...(options.headers || {})
    };

    if (token) {
        headers["Authorization"] =
            "Bearer " + token;
    }

    const response = await fetch(url, {
        ...options,
        headers
    });

    let data = {};

    try {
        data = await response.json();
    } catch (error) {
        data = {};
    }

    if (!response.ok) {

        if (response.status === 401) {

            clearAuth();

            window.location.href =
                "index.html";
        }

        throw new Error(
            data.error ||
            data.message ||
            "Ocurrió un error en la solicitud."
        );
    }

    return data;
}

// MENSAJES

function showMessage(message, type = "success") {

    let container =
        document.getElementById("message");

    if (!container) {
        alert(message);
        return;
    }

    container.className =
        "message " + type;

    container.textContent = message;

    setTimeout(() => {

        container.textContent = "";
        container.className = "message";

    }, 4000);
}


// ESTRUCTURA GENERAL

function setupShell() {

    const user = getUser();

    const userName =
        document.getElementById("userName");

    if (userName && user) {
        userName.textContent =
            user.nombre || user.correo;
    }

    const logoutButton =
        document.getElementById("logoutButton");

    if (logoutButton) {

        logoutButton.addEventListener(
            "click",
            logout
        );
    }
}