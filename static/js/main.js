
document.addEventListener("DOMContentLoaded", function () {
    // Automatically update the copyright year.
    const yearElement = document.getElementById("currentYear");

    if (yearElement) {
        yearElement.textContent = new Date().getFullYear();
    }

    // Initialise the Bootstrap aircraft carousel.
    const carouselElement = document.getElementById("aircraftCarousel");

    if (carouselElement && window.bootstrap) {
        bootstrap.Carousel.getOrCreateInstance(carouselElement, {
            interval: 5000,
            ride: "carousel",
            pause: "hover",
            wrap: true
        });
    }
});
