// Apply theme immediately to prevent screen flashing using document.documentElement
(function() {
    const theme = localStorage.getItem('theme');
    if (theme === 'light') {
        document.documentElement.classList.add('light-mode');
    }
})();

// Global function for pages with hardcoded onclick="toggleTheme()"
function toggleTheme() {
    const isLight = document.documentElement.classList.toggle('light-mode');
    if (document.body) {
        document.body.classList.toggle('light-mode', isLight);
    }
    localStorage.setItem('theme', isLight ? 'light' : 'dark');
    
    // Update all theme toggle buttons on the page
    const buttons = document.querySelectorAll('.theme-switch, #theme-toggle');
    buttons.forEach(btn => {
        btn.innerHTML = isLight ? '🌙 Dark' : '☀️ Light';
    });
}

document.addEventListener('DOMContentLoaded', () => {
    // Make sure body class matches documentElement class
    const isLight = document.documentElement.classList.contains('light-mode');
    if (isLight) {
        document.body.classList.add('light-mode');
    } else {
        document.body.classList.remove('light-mode');
    }

    const header = document.querySelector('header');
    if (header) {
        let navLinks = header.querySelector('.nav-links');
        if (!navLinks) {
            navLinks = document.createElement('div');
            navLinks.className = 'nav-links';
            header.appendChild(navLinks);
        }
        
        // Only append if it doesn't already exist
        const existingBtn = document.getElementById('theme-toggle') || header.querySelector('.theme-switch');
        if (!existingBtn) {
            const toggleBtn = document.createElement('button');
            toggleBtn.id = 'theme-toggle';
            toggleBtn.className = 'theme-switch';
            toggleBtn.type = 'button';
            toggleBtn.style.marginLeft = '1rem';
            toggleBtn.innerHTML = isLight ? '🌙 Dark' : '☀️ Light';
            toggleBtn.addEventListener('click', toggleTheme);
            navLinks.appendChild(toggleBtn);
        } else {
            // Update labels of existing buttons
            existingBtn.innerHTML = isLight ? '🌙 Dark' : '☀️ Light';
            // Bind toggleTheme if not already done or if it's onclick
            if (!existingBtn.onclick) {
                existingBtn.addEventListener('click', toggleTheme);
            }
        }
    }
    
    // Update any other theme buttons on the page
    const buttons = document.querySelectorAll('.theme-switch, #theme-toggle');
    buttons.forEach(btn => {
        btn.innerHTML = isLight ? '🌙 Dark' : '☀️ Light';
    });
});

