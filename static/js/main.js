// Auto-hide alert messages after 5 seconds
document.addEventListener("DOMContentLoaded", function () {
    document.querySelectorAll(".alert-dismissible").forEach(function (alertBox) {
        setTimeout(function () {
            const alert = bootstrap.Alert.getOrCreateInstance(alertBox);
            alert.close();
        }, 5000);
    });
});