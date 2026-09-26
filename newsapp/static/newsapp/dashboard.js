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

    // Live Date Display
    const dateEl = document.getElementById("live-date");
    if (dateEl) {
        const now = new Date();
        const options = { weekday: 'short', month: 'short', day: 'numeric', year: 'numeric' };
        dateEl.textContent = `📅 ${now.toLocaleDateString('en-US', options).toUpperCase()}`;
    }

    // Live Weather via Open-Meteo API
    const weatherEl = document.getElementById("live-weather");
    if (weatherEl) {
        async function fetchWeather(lat, lon, cityName = "Local") {
            try {
                const res = await fetch(`https://api.open-meteo.com/v1/forecast?latitude=${lat}&longitude=${lon}&current_weather=true`);
                if (!res.ok) throw new Error("Weather fetch failed");
                const data = await res.json();
                const temp = Math.round(data.current_weather.temperature);
                const code = data.current_weather.weathercode;
                let icon = "🌤️";
                if (code === 0) icon = "☀️";
                else if (code >= 1 && code <= 3) icon = "⛅";
                else if (code >= 51 && code <= 67) icon = "🌧️";
                else if (code >= 71) icon = "❄️";
                else if (code >= 95) icon = "🌩️";
                weatherEl.textContent = `${icon} ${temp}°C ${cityName}`;
            } catch (err) {
                weatherEl.textContent = "🌤️ 24°C Global";
            }
        }

        if (navigator.geolocation) {
            navigator.geolocation.getCurrentPosition(
                (pos) => fetchWeather(pos.coords.latitude, pos.coords.longitude, "Local"),
                () => fetchWeather(40.7128, -74.0060, "New York")
            );
        } else {
            fetchWeather(40.7128, -74.0060, "New York");
        }
    }

    // Theme Management System
    function setTheme(theme) {
        root.dataset.theme = theme;
        localStorage.setItem("news_theme", theme);
        if (themeButton) {
            themeButton.textContent = theme === "dark" ? "🌞 Theme" : "🌙 Theme";
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

    const colors = ['#dc2626', '#ef4444', '#fbbf24', '#e11d48'];
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
                const dx = p.x - p2.x;
                const dy = p.y - p2.y;
                const dist = Math.sqrt(dx * dx + dy * dy);
                if (dist < 110) {
                    ctx.beginPath();
                    ctx.moveTo(p.x, p.y);
                    ctx.lineTo(p2.x, p2.y);
                    ctx.strokeStyle = p.color;
                    ctx.globalAlpha = (1 - dist / 110) * 0.25;
                    ctx.stroke();
                    ctx.globalAlpha = 1;
                }
            }
        });
        requestAnimationFrame(renderParticles);
    }
    renderParticles();

    // Bookmark Interaction Handling
    function initBookmarkButton(btn) {
        btn.addEventListener("click", async (e) => {
            e.preventDefault();
            e.stopPropagation();
            const title = btn.dataset.title;
            const url = btn.dataset.url;
            const image = btn.dataset.image || "";

            if (!url) return;

            btn.disabled = true;
            const origText = btn.innerHTML;
            btn.innerHTML = "⌛ Saving...";

            try {
                const formData = new FormData();
                formData.append("title", title);
                formData.append("url", url);
                formData.append("image", image);

                const response = await fetch("/save/", {
                    method: "POST",
                    headers: {
                        "X-CSRFToken": getCsrfToken(),
                        "X-Requested-With": "XMLHttpRequest"
                    },
                    body: formData
                });

                const data = await response.json();
                if (response.ok && (data.status === "saved" || data.status === "exists")) {
                    btn.innerHTML = "✅ Bookmarked";
                    btn.classList.add("saved");
                    showToast(data.status === "saved" ? "Article saved to bookmarks!" : "Article already in bookmarks");
                    const countEl = document.querySelector(".bookmark-link .count");
                    if (countEl && data.status === "saved") {
                        countEl.textContent = parseInt(countEl.textContent || "0", 10) + 1;
                    }
                } else {
                    throw new Error(data.message || "Failed to save article");
                }
            } catch (err) {
                btn.innerHTML = origText;
                btn.disabled = false;
                showToast(err.message || "Could not save bookmark", true);
            }
        });
    }

    document.querySelectorAll(".bookmark-button").forEach(initBookmarkButton);

    // In-App News Reader Modal Handler
    const readerModal = document.getElementById("reader-modal");
    const closeReaderBtn = document.getElementById("close-reader-modal");
    const modalSource = document.getElementById("modal-source");
    const modalReadingTime = document.getElementById("modal-reading-time");
    const modalTimeAgo = document.getElementById("modal-time-ago");
    const modalTitle = document.getElementById("modal-title");
    const modalMediaWrap = document.getElementById("modal-media-wrap");
    const modalImage = document.getElementById("modal-image");
    const modalDescription = document.getElementById("modal-description");
    const modalBookmarkBtn = document.getElementById("modal-bookmark-btn");
    const modalSourceLink = document.getElementById("modal-source-link");

    const modalParagraphs = document.getElementById("modal-paragraphs");

    async function openReaderModal(articleData) {
        if (!readerModal) return;
        if (modalSource) modalSource.textContent = articleData.source || "Global Feed";
        if (modalReadingTime) modalReadingTime.textContent = articleData.readingTime ? `⏱️ ${articleData.readingTime}` : '⏱️ 3 min read';
        if (modalTimeAgo) modalTimeAgo.textContent = articleData.timeAgo || 'Recently';
        if (modalTitle) modalTitle.textContent = articleData.title || "Untitled Article";
        if (modalDescription) modalDescription.textContent = articleData.description || "";

        if (modalImage && modalMediaWrap) {
            if (articleData.image) {
                modalImage.src = articleData.image;
                modalMediaWrap.style.display = "block";
            } else {
                modalMediaWrap.style.display = "none";
            }
        }

        if (modalSourceLink) modalSourceLink.href = articleData.url || "#";

        if (modalParagraphs) {
            modalParagraphs.innerHTML = `<p class="extracting-indicator">⚡ <i>Extracting full article content from original source...</i></p>`;
        }

        if (modalBookmarkBtn) {
            modalBookmarkBtn.dataset.title = articleData.title || "";
            modalBookmarkBtn.dataset.url = articleData.url || "";
            modalBookmarkBtn.dataset.image = articleData.image || "";
            modalBookmarkBtn.classList.remove("saved");
            modalBookmarkBtn.innerHTML = "❤️ Bookmark Story";
            const newBtn = modalBookmarkBtn.cloneNode(true);
            modalBookmarkBtn.parentNode.replaceChild(newBtn, modalBookmarkBtn);
            initBookmarkButton(newBtn);
        }

        readerModal.classList.add("active");
        readerModal.setAttribute("aria-hidden", "false");
        document.body.style.overflow = "hidden";

        if (articleData.url) {
            try {
                const res = await fetch(`/article/extract/?url=${encodeURIComponent(articleData.url)}`, {
                    headers: { "X-Requested-With": "XMLHttpRequest" }
                });
                const data = await res.json();
                if (data.status === "success" && data.article && data.article.paragraphs && data.article.paragraphs.length > 0) {
                    if (modalParagraphs) {
                        modalParagraphs.innerHTML = data.article.paragraphs.map(p => `<p>${p}</p>`).join("");
                    }
                    if (data.article.reading_time && modalReadingTime) {
                        modalReadingTime.textContent = `⏱️ ${data.article.reading_time}`;
                    }
                    if (data.article.lead_image && modalImage && modalMediaWrap) {
                        modalImage.src = data.article.lead_image;
                        modalMediaWrap.style.display = "block";
                    }
                } else {
                    if (modalParagraphs) {
                        modalParagraphs.innerHTML = `<p class="extracting-fallback"><i>Full story text extraction is limited by publisher paywall. Click below to read on original site.</i></p>`;
                    }
                }
            } catch (err) {
                if (modalParagraphs) {
                    modalParagraphs.innerHTML = `<p class="extracting-fallback"><i>Full story text extraction is limited by publisher paywall. Click below to read on original site.</i></p>`;
                }
            }
        }
    }

    function closeReaderModal() {
        if (!readerModal) return;
        readerModal.classList.remove("active");
        readerModal.setAttribute("aria-hidden", "true");
        document.body.style.overflow = "";
    }

    if (closeReaderBtn) closeReaderBtn.addEventListener("click", closeReaderModal);
    if (readerModal) {
        readerModal.addEventListener("click", (e) => {
            if (e.target === readerModal) closeReaderModal();
        });
    }
    window.addEventListener("keydown", (e) => {
        if (e.key === "Escape" && readerModal && readerModal.classList.contains("active")) {
            closeReaderModal();
        }
    });



    // Infinite Scroll Sentinel & Load More Handler
    const sentinel = document.getElementById("infinite-scroll-sentinel");
    if (sentinel) {
        const articleGrid = document.querySelector(".article-grid");
        const loadMoreBtn = document.getElementById("load-more-btn");
        const loader = document.getElementById("infinite-loader");
        let isLoading = false;
        let lastCategory = "";

        function createSkeletonCards() {
            const skeletons = [];
            for (let i = 0; i < 3; i++) {
                const card = document.createElement("article");
                card.className = "skeleton-card";
                card.innerHTML = `
                    <div class="skeleton-media"></div>
                    <div class="skeleton-body">
                        <div class="skeleton-line skeleton-title"></div>
                        <div class="skeleton-line skeleton-text-1"></div>
                        <div class="skeleton-line skeleton-text-2"></div>
                    </div>
                `;
                skeletons.push(card);
            }
            return skeletons;
        }

        async function loadMoreArticles() {
            const nextPage = sentinel.dataset.nextPage;
            if (!nextPage || isLoading) return;

            isLoading = true;
            if (loader) loader.style.display = "flex";

            const skeletons = createSkeletonCards();
            skeletons.forEach(s => articleGrid.appendChild(s));

            const category = sentinel.dataset.category || "general";
            const country = sentinel.dataset.country || "world";
            const query = sentinel.dataset.query || "";
            const fetchUrl = `/?category=${encodeURIComponent(category)}&country=${encodeURIComponent(country)}&q=${encodeURIComponent(query)}&page=${nextPage}&format=json`;

            try {
                const response = await fetch(fetchUrl, {
                    headers: { "X-Requested-With": "XMLHttpRequest" }
                });
                const data = await response.json();

                skeletons.forEach(s => s.remove());

                if (data.status === "success" && data.articles && data.articles.length > 0) {
                    if (data.category_name && lastCategory !== data.category_name) {
                        lastCategory = data.category_name;
                        const divider = document.createElement("div");
                        divider.className = "stream-section-divider";
                        divider.innerHTML = `<span>${data.category_name} Stream</span>`;
                        articleGrid.appendChild(divider);
                    }

                    data.articles.forEach(article => {
                        let badgeClass = "";
                        const catLower = (lastCategory || "").toLowerCase();
                        if (catLower.includes("tech")) badgeClass = "badge-tech";
                        else if (catLower.includes("business")) badgeClass = "badge-business";
                        else if (catLower.includes("world")) badgeClass = "badge-world";
                        else if (catLower.includes("science")) badgeClass = "badge-science";
                        else if (catLower.includes("sports")) badgeClass = "badge-sports";

                        const card = document.createElement("article");
                        card.className = "article-card";
                        card.innerHTML = `
                            <div class="card-media ${!article.urlToImage ? 'no-image' : ''}">
                                <span class="source-badge ${badgeClass}">${article.source ? article.source.name : 'Global Feed'}</span>
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
                        const bBtn = card.querySelector(".bookmark-button");
                        if (bBtn) initBookmarkButton(bBtn);
                        articleGrid.appendChild(card);
                    });

                    sentinel.dataset.nextPage = data.next_page || (parseInt(nextPage, 10) + 1);
                }
            } catch (err) {
                skeletons.forEach(s => s.remove());
                showToast("Failed to load more stories", true);
            } finally {
                isLoading = false;
                if (!sentinel.dataset.nextPage && loader) {
                    loader.style.display = "none";
                }
            }
        }

        if (loadMoreBtn) {
            loadMoreBtn.addEventListener("click", loadMoreArticles);
        }

        if ("IntersectionObserver" in window) {
            const observer = new IntersectionObserver((entries) => {
                entries.forEach(entry => {
                    if (entry.isIntersecting && sentinel.dataset.nextPage && !isLoading) {
                        loadMoreArticles();
                    }
                });
            }, {
                rootMargin: "350px 0px"
            });
            observer.observe(sentinel);
        } else {
            window.addEventListener("scroll", () => {
                if (sentinel.dataset.nextPage && (window.innerHeight + window.scrollY) >= document.body.offsetHeight - 600) {
                    loadMoreArticles();
                }
            });
        }
    }
})();
