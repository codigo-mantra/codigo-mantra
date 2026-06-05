// Scroll fade-in
const observer = new IntersectionObserver((entries) => {
    entries.forEach(e => {
        if (e.isIntersecting) {
            e.target.classList.add('visible');
            observer.unobserve(e.target);
        }
    });
}, { threshold: 0.1 });

document.querySelectorAll('.fade-up').forEach(el => observer.observe(el));


// $(document).ready(function () {
//     $('.ws-track').slick({
//         slidesToShow: 5.4,
//         slidesToScroll: 1,
//         arrows: false,
//         dots: false,
//         speed: 300,
//         infinite: true,
//         autoplaySpeed: 5000,
//         autoplay: true,
//         responsive: [
//             {
//                 breakpoint: 991,
//                 settings: {
//                     slidesToShow: 3,
//                 }
//             },
//             {
//                 breakpoint: 767,
//                 settings: {
//                     slidesToShow: 1,
//                 }
//             }
//         ]
//     });
// });

function toggleDesc(id) {
    const desc = document.getElementById('desc-' + id);
    const toggle = document.getElementById('toggle-' + id);
    const isExpanded = desc.classList.contains('expanded');

    // Close ALL others smoothly
    document.querySelectorAll('.job-desc').forEach(d => {
        d.style.height = d.scrollHeight + 'px'; // set explicit height first
        requestAnimationFrame(() => {
            requestAnimationFrame(() => {
                d.style.height = '24px';
                d.classList.remove('expanded');
            });
        });
    });
    document.querySelectorAll('.btn-toggle').forEach(t => t.classList.remove('open'));

    // Open clicked one
    if (!isExpanded) {
        const fullHeight = desc.scrollHeight;
        desc.style.height = '24px';

        requestAnimationFrame(() => {
            requestAnimationFrame(() => {
                desc.style.height = fullHeight + 'px';
                desc.classList.add('expanded');
                toggle.classList.add('open');
            });
        });
    }
}

// ── MOBILE MENU ──
const mobileMenu = document.querySelector('.mobile-menu');
const menuBtn = document.querySelector('.menu-btn');
const closeBtn = document.querySelector('.close-btn');

function toggleMobileMenu() {
    if (mobileMenu) mobileMenu.classList.toggle('active');
    if (menuBtn) menuBtn.classList.toggle('hidden');
    if (closeBtn) closeBtn.classList.toggle('hidden');
}

if (menuBtn) menuBtn.addEventListener('click', toggleMobileMenu);
if (closeBtn) closeBtn.addEventListener('click', toggleMobileMenu);


// ── ACCORDION ──
const accordionItems = document.querySelectorAll('.accordion-item');

accordionItems.forEach(item => {
    const header = item.querySelector('.accordion-header');
    const content = item.querySelector('.accordion-content');

    header.addEventListener('click', () => {
        const isActive = item.classList.contains('active');

        // Close all other items
        accordionItems.forEach(i => {
            i.classList.remove('active');
        });

        // Open clicked item
        if (!isActive) {
            item.classList.add('active');
        }
    });
});


// ── SMOOTH SCROLL ──
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function (e) {
        e.preventDefault();
        const target = document.querySelector(this.getAttribute('href'));
        if (target) {
            target.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
    });
});


// ── FORM VALIDATION ──
const contactForm = document.getElementById('contactForm');
const applyForm = document.getElementById('applyForm');

function validateEmail(email) {
    const re = /^[A-Za-z0-9][A-Za-z0-9._%+-]*@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$/;
    return re.test(String(email).toLowerCase());
}

function validatePhone(phone) {
    const digits = String(phone).replace(/\D/g, "");
    if (digits.length !== 10) return false;
    if (/^0{10}$/.test(digits)) return false;
    return true;
}

function showMessage(form, type, message) {
    const msg = form.querySelector('.form-message');
    msg.textContent = message;
    msg.className = `form-message ${type}`;
    msg.style.display = 'block';
    setTimeout(() => msg.style.display = 'none', 3000);
}

if (contactForm) {
    contactForm.addEventListener('submit', function (e) {
        e.preventDefault();

        const name = document.getElementById('contactName').value;
        const email = document.getElementById('contactEmail').value;
        const phone = document.getElementById('contactPhone').value;
        const message = document.getElementById('contactMessage').value;

        if (!name || !email || !phone || !message) {
            showMessage(this, 'error', 'Please fill in all fields');
            return;
        }

        if (!validateEmail(email)) {
            showMessage(this, 'error', 'Please enter a valid email');
            return;
        }

        if (!validatePhone(phone)) {
            showMessage(this, 'error', 'Please enter a valid phone number');
            return;
        }

        // Submit form
        showMessage(this, 'success', 'Message sent successfully!');
        this.reset();
    });
}

if (applyForm) {
    applyForm.addEventListener('submit', function (e) {
        e.preventDefault();

        const name = document.getElementById('applyName').value;
        const email = document.getElementById('applyEmail').value;
        const phone = document.getElementById('applyPhone').value;
        const position = document.getElementById('applyPosition').value;
        const resume = document.getElementById('applyResume').value;

        if (!name || !email || !phone || !position || !resume) {
            showMessage(this, 'error', 'Please fill in all fields');
            return;
        }

        if (!validateEmail(email)) {
            showMessage(this, 'error', 'Please enter a valid email');
            return;
        }

        if (!validatePhone(phone)) {
            showMessage(this, 'error', 'Please enter a valid phone number');
            return;
        }

        // Submit form
        showMessage(this, 'success', 'Application submitted successfully!');
        this.reset();
    });
}

const toggle = document.getElementById("cs-toggle-input");
const industriesList = document.getElementById("list-industries");
const techList = document.getElementById("list-technologies");

toggle.addEventListener("change", function () {
    if (this.checked) {
        industriesList.classList.remove("active");
        techList.classList.add("active");
    } else {
        industriesList.classList.add("active");
        techList.classList.remove("active");
    }
});


document.addEventListener("DOMContentLoaded", function () {

    const filters = document.querySelectorAll('input[name="cs-filter"]');
    const cards = document.querySelectorAll('.cs-card');
    const allBtn = document.getElementById("cs-all-btn");

    function applyFilters() {

        let selected = [];

        filters.forEach(cb => {
            if (cb.checked) {
                selected.push(cb.value.toLowerCase());
            }
        });

        cards.forEach(card => {

            const industries = card.dataset.industries || "";
            const technologies = card.dataset.technologies || "";

            // If no filters selected → show all
            if (selected.length === 0) {
                card.style.display = "block";
                return;
            }

            // Match if ANY filter matches industry OR tech
            let match = selected.some(val =>
                industries.includes(val) || technologies.includes(val)
            );

            card.style.display = match ? "block" : "none";
        });
    }

    // Trigger on checkbox change
    filters.forEach(cb => {
        cb.addEventListener("change", applyFilters);
    });

    // "All" button reset
    if (allBtn) {
        allBtn.addEventListener("click", function () {
            filters.forEach(cb => cb.checked = false);
            applyFilters();
        });
    }

});