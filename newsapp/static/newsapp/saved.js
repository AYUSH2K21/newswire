(() => {
    const container = document.getElementById("toast-container");
    const csrfToken = document.querySelector('meta[name="csrf-token"]').content;
    function notify(message, error = false) {
        container.innerHTML = "";
        const toast = document.createElement("div");
        toast.className = error ? "toast error" : "toast";
        toast.textContent = message;
        container.appendChild(toast);
        setTimeout(() => toast.remove(), 2500);
    }
    document.querySelectorAll(".remove-bookmark").forEach((button) => {
        button.addEventListener("click", async () => {
            if (!window.confirm("Remove this bookmark?")) return;
            const body = new URLSearchParams({article_id: button.dataset.articleId});
            try {
                const response = await fetch("/delete/", {method:"POST", headers:{"Content-Type":"application/x-www-form-urlencoded","X-CSRFToken":csrfToken}, body});
                const data = await response.json();
                if (!response.ok) throw new Error(data.message || "Unable to remove bookmark");
                document.getElementById(`bookmark-card-${button.dataset.articleId}`)?.remove();
                notify("Bookmark removed");
            } catch (error) { notify(error.message, true); }
        });
    });
})();
