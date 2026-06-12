(() => {
    const root = document.documentElement;
    const themeButton = document.getElementById("theme-toggle");
    const toast = document.getElementById("toast");

    function setTheme(theme) {
        root.dataset.theme = theme;
        localStorage.setItem("news_theme", theme);
        themeButton.textContent = theme === "dark" ? "Light mode" : "Dark mode";
    }

    function showToast(message, error = false) {
        toast.textContent = message;
        toast.className = error ? "show error" : "show";
        window.setTimeout(() => { toast.className = ""; }, 2400);
    }

    setTheme(root.dataset.theme === "light" ? "light" : "dark");
    themeButton.addEventListener("click", () => {
        setTheme(root.dataset.theme === "dark" ? "light" : "dark");
    });

    document.querySelectorAll(".bookmark-button").forEach((button) => {
        button.addEventListener("click", async () => {
            const body = new URLSearchParams({
                title: button.dataset.title,
                url: button.dataset.url,
                image: button.dataset.image || "",
            });
            try {
                const response = await fetch("/save/", {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/x-www-form-urlencoded",
                        "X-CSRFToken": document.querySelector('meta[name="csrf-token"]').content,
                    },
                    body,
                });
                const data = await response.json();
                if (!response.ok) throw new Error(data.message || "Unable to bookmark article");
                button.classList.add("saved");
                button.textContent = "Bookmarked";
                showToast(data.status === "exists" ? "Article is already bookmarked" : "Article bookmarked");
            } catch (error) {
                showToast(error.message, true);
            }
        });
    });
})();
