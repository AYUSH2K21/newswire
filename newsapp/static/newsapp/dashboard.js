(() => {
    const root = document.documentElement;
    const themeButton = document.getElementById("theme-toggle");
    const toast = document.getElementById("toast");
    const searchInput = document.getElementById("search-input");

    // Scroll Progress Line
    const progressBar = document.getElementById("scroll-progress") || document.createElement("div");
    if (!progressBar.id) {
        progressBar.id = "scroll-progress";
        document.body.prepend(progressBar);
    }

    window.addEventListener("scroll", () => {
        const totalHeight = document.documentElement.scrollHeight - window.innerHeight;
        const progress = totalHeight > 0 ? (window.scrollY / totalHeight) * 100 : 0;
        progressBar.style.width = `${progress}%`;
    });

    // Theme Management
    function setTheme(theme) {
        root.dataset.theme = theme;
        localStorage.setItem("news_theme", theme);
        if (themeButton) {
            themeButton.textContent = theme === "dark" ? "☀️ Theme" : "🌙 Theme";
        }
    }

    setTheme(root.dataset.theme === "light" ? "light" : "dark");
    if (themeButton) {
        themeButton.addEventListener("click", () => {
            setTheme(root.dataset.theme === "dark" ? "light" : "dark");
        });
    }

    // Keyboard Shortcut ⌘K / Ctrl+K / / to Focus Search
    window.addEventListener("keydown", (e) => {
        if ((e.ctrlKey && e.key.toLowerCase() === "k") || (e.metaKey && e.key.toLowerCase() === "k") || (e.key === "/" && document.activeElement !== searchInput)) {
            e.preventDefault();
            if (searchInput) {
                searchInput.focus();
                searchInput.select();
            }
        }
    });

    // Toast Notification System
    function showToast(message, error = false) {
        if (!toast) return;
        toast.textContent = message;
        toast.className = error ? "show error" : "show";
        window.setTimeout(() => { toast.className = ""; }, 2600);
    }

    // CSRF Token Helper
    function getCsrfToken() {
        const csrfMeta = document.querySelector('meta[name="csrf-token"]');
        if (csrfMeta && csrfMeta.content) return csrfMeta.content;
        const cookieValue = document.cookie
            .split('; ')
            .find(row => row.startsWith('csrftoken='))
            ?.split('=')[1];
        return cookieValue || "";
    }

    // 60FPS Ambient Particle Constellation Canvas
    const canvas = document.createElement("canvas");
    canvas.id = "ambient-canvas";
    canvas.style.cssText = "position:fixed;inset:0;pointer-events:none;z-index:0;opacity:0.45;";
    document.body.prepend(canvas);

    const ctx = canvas.getContext("2d");
    let particles = [];

    function resizeCanvas() {
        canvas.width = window.innerWidth;
        canvas.height = window.innerHeight;
    }
    resizeCanvas();
    window.addEventListener("resize", resizeCanvas);

    const colors = ['#00f2fe', '#a855f7', '#ff007f', '#00f5d4'];
    const particleCount = Math.min(45, Math.floor(window.innerWidth / 32));

    for (let i = 0; i < particleCount; i++) {
        particles.push({
            x: Math.random() * canvas.width,
            y: Math.random() * canvas.height,
            vx: (Math.random() - 0.5) * 0.4,
            vy: (Math.random() - 0.5) * 0.4,
            size: Math.random() * 2 + 1,
            color: colors[Math.floor(Math.random() * colors.length)]
        });
    }

    function renderParticles() {
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        particles.forEach((p, index) => {
            p.x += p.vx;
            p.y += p.vy;
            if (p.x < 0 || p.x > canvas.width) p.vx *= -1;
            if (p.y < 0 || p.y > canvas.height) p.vy *= -1;

            ctx.beginPath();
            ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
            ctx.fillStyle = p.color;
            ctx.fill();

            for (let j = index + 1; j < particles.length; j++) {
                const p2 = particles[j];
                const dist = Math.hypot(p.x - p2.x, p.y - p2.y);
                if (dist < 120) {
                    ctx.beginPath();
                    ctx.moveTo(p.x, p.y);
                    ctx.lineTo(p2.x, p2.y);
                    ctx.strokeStyle = p.color;
                    ctx.globalAlpha = (1 - dist / 120) * 0.2;
                    ctx.lineWidth = 0.6;
                    ctx.stroke();
                    ctx.globalAlpha = 1;
                }
            }
        });
        requestAnimationFrame(renderParticles);
    }
    renderParticles();

    // Mouse Parallax Physics for Ambient Orbs
    const bubbles = document.querySelectorAll(".ambient-bubbles .bubble");
    if (bubbles.length > 0) {
        let mouseX = 0;
        let mouseY = 0;
        let currentX = 0;
        let currentY = 0;

        window.addEventListener("mousemove", (e) => {
            mouseX = (e.clientX - window.innerWidth / 2) * 0.04;
            mouseY = (e.clientY - window.innerHeight / 2) * 0.04;
        });

        function animateParallax() {
            currentX += (mouseX - currentX) * 0.08;
            currentY += (mouseY - currentY) * 0.08;

            bubbles.forEach((bubble, index) => {
                const factor = (index + 1) * 0.4;
                bubble.style.transform = `translate(${currentX * factor}px, ${currentY * factor}px)`;
            });

            requestAnimationFrame(animateParallax);
        }

        animateParallax();
    }

    // 3D Tilt Micro-Interactions on Article Cards
    function initCardTilt(card) {
        card.addEventListener("mousemove", (e) => {
            const rect = card.getBoundingClientRect();
            const x = e.clientX - rect.left - rect.width / 2;
            const y = e.clientY - rect.top - rect.height / 2;
            card.style.transform = `perspective(1000px) rotateX(${(-y / rect.height) * 8}deg) rotateY(${(x / rect.width) * 8}deg) translateY(-6px)`;
        });

        card.addEventListener("mouseleave", () => {
            card.style.transform = "perspective(1000px) rotateX(0deg) rotateY(0deg) translateY(0px)";
        });
    }

    document.querySelectorAll(".article-card, .stack-card").forEach(initCardTilt);

    // Floating Back-To-Top Button
    const topButton = document.createElement("button");
    topButton.id = "back-to-top";
    topButton.type = "button";
    topButton.innerHTML = "↑";
    topButton.setAttribute("aria-label", "Scroll back to top");
    document.body.appendChild(topButton);

    window.addEventListener("scroll", () => {
        if (window.scrollY > 350) {
            topButton.classList.add("visible");
        } else {
            topButton.classList.remove("visible");
        }
    });

    topButton.addEventListener("click", () => {
        window.scrollTo({ top: 0, behavior: "smooth" });
    });

    // Bookmark Button Event Binding
    function initBookmarkButton(button) {
        button.addEventListener("click", async () => {
            const token = getCsrfToken();
            const body = new URLSearchParams({
                title: button.dataset.title || "",
                url: button.dataset.url || "",
                image: button.dataset.image || "",
            });

            try {
                const response = await fetch("/save/", {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/x-www-form-urlencoded",
                        "X-CSRFToken": token,
                    },
                    body,
                });
                const data = await response.json();
                if (!response.ok) throw new Error(data.message || "Unable to bookmark article");
                button.classList.add("saved");
                button.textContent = "💖 Bookmarked";
                showToast(data.status === "exists" ? "Article is already in your bookmarks!" : "Article saved to bookmarks!");
            } catch (error) {
                showToast(error.message, true);
            }
        });
    }

    document.querySelectorAll(".bookmark-button").forEach(initBookmarkButton);

    // Infinite Scroll / Dynamic Load More Handler
    const sentinel = document.getElementById("infinite-scroll-sentinel");
    const loadMoreBtn = document.getElementById("load-more-btn");
    const articleGrid = document.querySelector(".article-grid");

    if (sentinel && articleGrid) {
        let isLoading = false;

        async function loadMoreArticles() {
            const nextPage = sentinel.dataset.nextPage;
            if (!nextPage || isLoading) return;

            isLoading = true;
            if (loadMoreBtn) {
                loadMoreBtn.classList.add("loading");
                loadMoreBtn.textContent = "⌛ Loading more stories...";
            }

            const category = sentinel.dataset.category || "general";
            const query = sentinel.dataset.query || "";
            const fetchUrl = `/?category=${encodeURIComponent(category)}&q=${encodeURIComponent(query)}&page=${nextPage}&format=json`;

            try {
                const response = await fetch(fetchUrl, {
                    headers: { "X-Requested-With": "XMLHttpRequest" }
                });
                const data = await response.json();

                if (data.status === "success" && data.articles) {
                    data.articles.forEach(article => {
                        const card = document.createElement("article");
                        card.className = "article-card";
                        card.innerHTML = `
                            <div class="card-media ${!article.urlToImage ? 'no-image' : ''}">
                                <span class="source-badge">${article.source ? article.source.name : 'Global Feed'}</span>
                                ${article.urlToImage ? `<img src="${article.urlToImage}" alt="" loading="lazy" onerror="this.style.display='none'; this.parentElement.classList.add('no-image');">` : ''}
                            </div>
                            <div class="card-body">
                                <div class="article-meta">
                                    <span>⏱️ ${article.estimated_reading_time || '3 min read'}</span>
                                    <time>${article.time_ago || 'Recently'}</time>
                                </div>
                                <h3><a href="${article.url}" target="_blank" rel="noopener noreferrer">${article.title}</a></h3>
                                <p>${article.description || 'Click below to open full article coverage.'}</p>
                                <div class="card-actions">
                                    <button class="bookmark-button" type="button" data-title="${article.title}" data-url="${article.url}" data-image="${article.urlToImage || ''}">❤️ Bookmark</button>
                                    <a class="read-link" href="${article.url}" target="_blank" rel="noopener noreferrer">Read Story →</a>
                                </div>
                            </div>
                        `;
                        initCardTilt(card);
                        const bBtn = card.querySelector(".bookmark-button");
                        if (bBtn) initBookmarkButton(bBtn);
                        articleGrid.appendChild(card);
                    });

                    if (data.has_next) {
                        sentinel.dataset.nextPage = data.next_page;
                        if (loadMoreBtn) {
                            loadMoreBtn.classList.remove("loading");
                            loadMoreBtn.textContent = "⚡ Load More Stories";
                        }
                    } else {
                        sentinel.dataset.nextPage = "";
                        if (loadMoreBtn) loadMoreBtn.remove();
                    }
                }
            } catch (err) {
                showToast("Failed to load more stories", true);
                if (loadMoreBtn) {
                    loadMoreBtn.classList.remove("loading");
                    loadMoreBtn.textContent = "⚡ Load More Stories";
                }
            } finally {
                isLoading = false;
            }
        }

        if (loadMoreBtn) {
            loadMoreBtn.addEventListener("click", loadMoreArticles);
        }

        window.addEventListener("scroll", () => {
            if (sentinel.dataset.nextPage && (window.innerHeight + window.scrollY) >= document.body.offsetHeight - 600) {
                loadMoreArticles();
            }
        });
    }
})();
