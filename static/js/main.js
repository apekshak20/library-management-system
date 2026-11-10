document.addEventListener("DOMContentLoaded", function () {
    // Auto-hide alert messages after 5 seconds
    document.querySelectorAll(".alert-dismissible").forEach(function (alertBox) {
        setTimeout(function () {
            const alert = bootstrap.Alert.getOrCreateInstance(alertBox);
            alert.close();
        }, 5000);
    });

    // Open and close the sidebar on mobile
    const toggle = document.getElementById("sidebarToggle");
    const sidebar = document.getElementById("sidebar");

    if (toggle && sidebar) {
        toggle.addEventListener("click", function () {
            sidebar.classList.toggle("open");
        });

        // Close the sidebar when the user clicks outside it
        document.addEventListener("click", function (event) {
            const clickedInside = sidebar.contains(event.target) || toggle.contains(event.target);
            if (!clickedInside) {
                sidebar.classList.remove("open");
            }
        });
    }

    // Ask for confirmation before deleting anything
    document.querySelectorAll(".delete-form").forEach(function (form) {
        form.addEventListener("submit", function (event) {
            const name = form.dataset.name || "this record";
            if (!confirm("Delete " + name + "? This cannot be undone.")) {
                event.preventDefault();
            }
        });
    });

    // Generic confirmation for forms with class "confirm-form"
    document.querySelectorAll(".confirm-form").forEach(function (form) {
        form.addEventListener("submit", function (event) {
            if (!confirm(form.dataset.confirm || "Are you sure?")) {
                event.preventDefault();
            }
        });
    });

});