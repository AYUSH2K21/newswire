(() => {
    function getCsrfToken() {
        const csrfMeta = document.querySelector('meta[name="csrf-token"]');
        if (csrfMeta && csrfMeta.content) return csrfMeta.content;
        const cookieValue = document.cookie
            .split('; ')
            .find(row => row.startsWith('csrftoken='))
            ?.split('=')[1];
        return cookieValue || "";
    }

    function showToast(message, error = false) {
        const container = document.getElementById("toast-container");
        if (!container) return;
        const toast = document.createElement("div");
        toast.className = error ? "toast error" : "toast";
        toast.textContent = message;
        container.appendChild(toast);
        window.setTimeout(() => { toast.remove(); }, 2600);
    }

    document.querySelectorAll(".remove-bookmark").forEach((button) => {
        button.addEventListener("click", async () => {
            const articleId = button.dataset.articleId;
            const card = document.getElementById(`bookmark-card-${articleId}`);
            const token = getCsrfToken();

            try {
                const response = await fetch("/delete/", {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/x-www-form-urlencoded",
                        "X-CSRFToken": token,
                    },
                    body: new URLSearchParams({ article_id: articleId }),
                });
                const data = await response.json();
                if (!response.ok) throw new Error(data.message || "Failed to remove bookmark");
                if (card) {
                    card.style.transition = "all 0.3s ease";
                    card.style.opacity = "0";
                    card.style.transform = "scale(0.9)";
                    window.setTimeout(() => card.remove(), 300);
                }
                showToast("Bookmark removed successfully");
            } catch (error) {
                showToast(error.message, true);
            }
        });
    });
})();
