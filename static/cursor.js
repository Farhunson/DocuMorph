// ==============================
// Cyberpunk Cursor Controller
// ==============================

// Default cursor paths
const cursors = {
    default: "/static/cursors/arrow.cur",
    pointer: "/static/cursors/link.cur",
    text: "/static/cursors/beam.cur",
    busy: "/static/cursors/busy.ani",
    wait: "/static/cursors/wait.ani"
};

// Apply the default cursor on page load
document.addEventListener("DOMContentLoaded", () => {
    document.body.style.cursor = `url('${cursors.default}'), auto`;
});

// Change cursor to pointer when hovering clickable buttons or links
document.addEventListener("mouseover", (e) => {
    if (e.target.closest("button, a, .card")) {
        document.body.style.cursor = `url('${cursors.pointer}'), pointer`;
    }
});

document.addEventListener("mouseout", (e) => {
    if (e.target.closest("button, a, .card")) {
        document.body.style.cursor = `url('${cursors.default}'), auto`;
    }
});

// Change cursor to text when focusing input fields
document.addEventListener("mouseover", (e) => {
    if (e.target.tagName === "INPUT" || e.target.tagName === "TEXTAREA") {
        document.body.style.cursor = `url('${cursors.text}'), text`;
    }
});

document.addEventListener("mouseout", (e) => {
    if (e.target.tagName === "INPUT" || e.target.tagName === "TEXTAREA") {
        document.body.style.cursor = `url('${cursors.default}'), auto`;
    }
});

// ==============================
// Loading Cursor Functions
// ==============================

function showLoadingCursor() {
    document.body.style.cursor = `url('${cursors.busy}'), wait`;
}

function hideLoadingCursor() {
    document.body.style.cursor = `url('${cursors.default}'), auto`;
}

// ==============================
// Auto-Hide Loading Cursor after AJAX or Form Submits
// ==============================
document.addEventListener("submit", () => {
    showLoadingCursor();
    setTimeout(hideLoadingCursor, 5000); // fallback after 5 seconds
});

// Expose functions globally
window.showLoadingCursor = showLoadingCursor;
window.hideLoadingCursor = hideLoadingCursor;
