// AUTENTICACIÓN Y SESIÓN

function getToken() {
    return localStorage.getItem("adoptapet_token");
}

function getUser() {
    const user = localStorage.getItem("adoptapet_user");

    if (!user) {
        return null;
    }

    try {
        return JSON.parse(user);
    } catch (error) {
        return null;
    }
}

function saveAuth(data) {

    if (data.token) {
        localStorage.setItem(
            "adoptapet_token",
            data.token
        );
    }

    if (data.usuario) {
        localStorage.setItem(
            "adoptapet_user",
            JSON.stringify(data.usuario)
        );
    }
}

function clearAuth() {
    localStorage.removeItem("adoptapet_token");
    localStorage.removeItem("adoptapet_user");
}

function requireAuth() {

    const token = getToken();

    if (!token) {
        window.location.href = "index.html";
        return false;
    }

    return true;
}

async function logout() {

    try {

        const token = getToken();

        await fetch(
            API.USUARIOS + "/logout",
            {
                method: "POST",
                headers: {
                    "Authorization": "Bearer " + token
                }
            }
        );

    } catch (error) {

        console.warn(
            "No se pudo contactar al servidor para cerrar sesión."
        );

    } finally {

        clearAuth();

        window.location.href = "index.html";
    }
}