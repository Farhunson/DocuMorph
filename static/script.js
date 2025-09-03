document.addEventListener("DOMContentLoaded", function () {
  const burger = document.querySelector('.burger-menu');
  const popup = document.querySelector('.burger-popup');
  const closeBtn = document.querySelector('.close-btn');

  if (burger && popup && closeBtn) {
    burger.addEventListener('click', () => {
      popup.style.display = 'block';
    });

    closeBtn.addEventListener('click', () => {
      popup.style.display = 'none';
    });
  }


  const form = document.getElementById("uploadForm");
  if (!form) return;

  const progressWrapper = document.getElementById("progressWrapper");
  const progressBar = document.getElementById("progressBar");
  const progressText = document.getElementById("progressText");
  const downloadLink = document.getElementById("downloadLink");

  form.addEventListener("submit", function (e) {
    e.preventDefault();

    // reset UI
    if (progressWrapper) {
      progressWrapper.style.display = "block";
      progressBar.style.width = "0%";
      progressText.textContent = "0%";
    }
    if (downloadLink) downloadLink.innerHTML = "";

    const formData = new FormData(form);

    fetch(window.location.pathname, {
      method: "POST",
      body: formData,
      headers: { "X-Requested-With": "XMLHttpRequest" }
    })
      .then(async (res) => {
        // If the route didn't return JSON, show an error to help debugging
        const ct = res.headers.get("content-type") || "";
        if (!ct.includes("application/json")) {
          const txt = await res.text();
          throw new Error("Server did not return JSON.\n\n" + txt);
        }
        return res.json();
      })
      .then((data) => {
        if (!data.task_id) {
          throw new Error("No task_id from server.");
        }

        const taskId = data.task_id;

        const interval = setInterval(() => {
          fetch(`/progress/${taskId}`)
            .then((r) => r.json())
            .then((p) => {
              const prog = p.progress ?? 0;
              progressBar.style.width = prog + "%";
              progressText.textContent = prog + "%";

              if (p.status === "error") {
                clearInterval(interval);
                downloadLink.innerHTML = `<div style="color:#E13B34;font-weight:600;">${p.error || "Conversion failed."}</div>`;
              } else if (p.status === "done" && p.download_url) {
                clearInterval(interval);
                progressBar.style.width = "100%";
                progressText.textContent = "100%";
                downloadLink.innerHTML = `<a class="result-btn" href="${p.download_url}">Download Result</a>`;
              }
            })
            .catch((err) => {
              clearInterval(interval);
              downloadLink.innerHTML = `<div style="color:#E13B34;font-weight:600;">${err.message}</div>`;
            });
        }, 500);
      })
      .catch((err) => {
        if (downloadLink) {
          downloadLink.innerHTML = `<div style="color:#E13B34;font-weight:600;">${err.message}</div>`;
        }
      });
  });
});



const filterBtns = document.querySelectorAll(".filter-btn");
const filterDropdown = document.querySelector(".filter-dropdown");
const cards = document.querySelectorAll(".card");

// --- BUTTON FILTER LOGIC ---
filterBtns.forEach(btn => {
  btn.addEventListener("click", () => {
    // Remove active class from all
    filterBtns.forEach(b => b.classList.remove("active"));
    btn.classList.add("active");

    const filter = btn.dataset.filter;
    applyFilter(filter);
  });
});

// --- DROPDOWN FILTER LOGIC ---
if (filterDropdown) {
  filterDropdown.addEventListener("change", () => {
    const filter = filterDropdown.value;
    applyFilter(filter);
  });
}

// --- SHARED FILTER FUNCTION ---
function applyFilter(filter) {
  cards.forEach(card => {
    if (filter === "all" || card.classList.contains(filter)) {
      card.style.display = "block";
    } else {
      card.style.display = "none";
    }
  });
}




document.addEventListener("DOMContentLoaded", function() {
  const title = document.getElementById("documorph-title");
  const originalText = title.textContent;
  const letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz1234567890@#$%&";
  let iteration = 0;

  // Set data-text for glitch effect overlay
  title.setAttribute("data-text", originalText);

  function hackEffect() {
    const interval = setInterval(() => {
      title.textContent = originalText
        .split("")
        .map((letter, index) => {
          if (index < iteration) {
            return originalText[index];
          }
          return letters[Math.floor(Math.random() * letters.length)];
        })
        .join("");

      if (iteration >= originalText.length) {
        clearInterval(interval);
        title.textContent = originalText; // Final locked text
      }

      iteration += 1 / 2; // Speed of locking letters
    }, 60); // Speed of shuffle
  }

  setTimeout(hackEffect, 500);
});




function updateFileName() {
  const fileInput = document.getElementById("fileInput");
  const fileName = document.getElementById("file-name");
  
  if (fileInput.files.length > 0) {
    if (fileInput.files.length === 1) {
      fileName.textContent = fileInput.files[0].name;
    } else {
      fileName.textContent = fileInput.files.length + " files selected";
    }
  } else {
    fileName.textContent = "No file selected";
  }
}

document.getElementById("fileInput").addEventListener("change", updateFileName);

/* BURGER MENU SCRIPT */
document.addEventListener("DOMContentLoaded", () => {
  const burger = document.querySelector(".burger-menu");
  const popup = document.querySelector(".burger-popup");
  const closeBtn = popup.querySelector(".close-btn");

  burger.addEventListener("click", () => {
    popup.classList.add("active");   // show popup
    burger.style.display = "none";   // hide burger
  });

  closeBtn.addEventListener("click", () => {
    popup.classList.remove("active"); 
    burger.style.display = "flex";   // show burger again
  });
});
