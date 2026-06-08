document.addEventListener('DOMContentLoaded', () => {
    const header = document.getElementById('main-header');
    if (!header) return;

    let lastScrollTop = 0;
    const delta = 5; // Minimum scroll amount before triggering

    window.addEventListener('scroll', () => {
        let currentScroll = window.pageYOffset || document.documentElement.scrollTop;

        // Make sure they scroll more than delta
        if (Math.abs(lastScrollTop - currentScroll) <= delta) {
            return;
        }

        // If scrolling down and scrolled past the header height
        if (currentScroll > lastScrollTop && currentScroll > header.offsetHeight) {
            // Scroll Down: Hide header
            header.classList.remove('translate-y-0');
            header.classList.add('-translate-y-full');
        } else {
            // Scroll Up: Show header
            header.classList.remove('-translate-y-full');
            header.classList.add('translate-y-0');
        }
        
        lastScrollTop = currentScroll <= 0 ? 0 : currentScroll; // For Mobile or negative scrolling
    });
});
