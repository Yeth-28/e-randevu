// DentalReserv - Ana JavaScript

// Alert'leri otomatik kapat
document.addEventListener('DOMContentLoaded', function () {
    const alerts = document.querySelectorAll('.alert-auto-close');
    alerts.forEach(function (alert) {
        setTimeout(function () {
            alert.style.opacity = '0';
            alert.style.transition = 'opacity 0.5s';
            setTimeout(() => alert.remove(), 500);
        }, 4000);
    });
});

// Silme onayı
function confirmDelete(message) {
    return confirm(message || 'Bu kaydı silmek istediğinize emin misiniz?');
}

// Aktif nav linkini işaretle
document.addEventListener('DOMContentLoaded', function () {
    const currentPath = window.location.pathname;
    document.querySelectorAll('.nav-link').forEach(function (link) {
        if (link.getAttribute('href') === currentPath) {
            link.classList.add('active');
        }
    });
});