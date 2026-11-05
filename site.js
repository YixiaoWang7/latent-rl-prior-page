"use strict";

(() => {
  const tasks = {
    pose: {
      name: "Target pose alignment",
      category: "Single arm · Unseen object",
      description: "Pick up an unseen brush and match its target pose.",
      steps: ["Grasp", "Reorient", "Align"],
      criterion: "All four object–target keypoint distances must be within 1.5 cm (strict) or 5 cm (relaxed) for 10 policy steps, not necessarily consecutive.",
      video: "./assets/videos/pose.mp4",
      poster: "./assets/images/pose-poster.webp",
    },
    door: {
      name: "Door lifting",
      category: "Single arm · New task",
      description: "Find the handle, grasp it, and lift the door above the cube.",
      steps: ["Reach", "Grasp", "Lift"],
      criterion: "Raise the bottom of the door above the cube. The cube’s height, color, and size, and the door’s position and orientation vary across episodes.",
      video: "./assets/videos/door.mp4",
      poster: "./assets/images/door-poster.webp",
    },
    assembly: {
      name: "Bimanual assembly",
      category: "Two arms · Shared single-arm prior",
      description: "Use two hands to align the parts and fit them together.",
      steps: ["Grasp", "Align", "Insert"],
      criterion: "Fully insert the cubic protrusion into the matching cavity. Success is measured by insertion depth relative to cavity depth.",
      video: "./assets/videos/assembly.mp4",
      poster: "./assets/images/assembly-poster.webp",
    },
  };

  const video = document.getElementById("task-video");
  const panel = document.getElementById("task-panel");
  const tabs = [...document.querySelectorAll("[data-task]")];
  let selectedTask = "pose";

  function selectTask(key, focus = false) {
    if (!Object.hasOwn(tasks, key)) return;
    const task = tasks[key];
    for (const tab of tabs) {
      const active = tab.dataset.task === key;
      tab.setAttribute("aria-selected", String(active));
      tab.tabIndex = active ? 0 : -1;
      if (active && focus) tab.focus();
    }
    panel.setAttribute("aria-labelledby", `tab-${key}`);
    document.getElementById("task-name").textContent = task.name;
    document.getElementById("task-category").textContent = task.category;
    document.getElementById("task-description").textContent = task.description;
    document.getElementById("task-criterion").textContent = task.criterion;
    task.steps.forEach((step, index) => {
      const label = document.getElementById(`task-step-${index + 1}`);
      if (label) label.textContent = step;
    });
    const download = document.getElementById("video-download");
    download.href = task.video;
    download.setAttribute("aria-label", `Download ${task.name.toLowerCase()} demonstration`);
    if (selectedTask !== key) {
      video.pause();
      video.poster = task.poster;
      video.querySelector("source").src = task.video;
      video.querySelector("a").href = task.video;
      video.setAttribute("aria-label", `${task.name} demonstration replay`);
      video.load();
      selectedTask = key;
    }
  }

  tabs.forEach((tab, index) => {
    tab.addEventListener("click", () => selectTask(tab.dataset.task));
    tab.addEventListener("keydown", (event) => {
      let next = index;
      if (event.key === "ArrowRight") next = (index + 1) % tabs.length;
      else if (event.key === "ArrowLeft") next = (index - 1 + tabs.length) % tabs.length;
      else if (event.key === "Home") next = 0;
      else if (event.key === "End") next = tabs.length - 1;
      else return;
      event.preventDefault();
      selectTask(tabs[next].dataset.task, true);
    });
  });
  document.querySelectorAll("[data-select-task]").forEach((link) => {
    link.addEventListener("click", () => selectTask(link.dataset.selectTask));
  });

  // Native links still open the image when JavaScript or dialog support is absent.
  const dialog = document.getElementById("figure-dialog");
  const enlarged = document.getElementById("enlarged-figure");
  let previousFocus = null;
  if (typeof dialog.showModal === "function") {
    document.querySelectorAll("[data-zoom]").forEach((link) => {
      link.addEventListener("click", (event) => {
        event.preventDefault();
        previousFocus = link;
        enlarged.src = link.href;
        enlarged.alt = link.querySelector("img").alt;
        document.getElementById("figure-dialog-title").textContent = link.dataset.zoom;
        dialog.showModal();
      });
    });
    document.getElementById("close-figure").addEventListener("click", () => dialog.close());
    dialog.addEventListener("click", (event) => {
      if (event.target !== dialog) return;
      const box = dialog.getBoundingClientRect();
      if (event.clientX < box.left || event.clientX > box.right ||
          event.clientY < box.top || event.clientY > box.bottom) dialog.close();
    });
    dialog.addEventListener("close", () => previousFocus?.focus());
  }

  const copy = document.getElementById("copy-citation");
  copy.addEventListener("click", async () => {
    const text = document.getElementById("citation-text").textContent;
    const status = document.getElementById("copy-status");
    try {
      if (!navigator.clipboard?.writeText) throw new Error("Clipboard unavailable");
      await navigator.clipboard.writeText(text);
      status.textContent = "BibTeX copied.";
      copy.textContent = "Copied";
      window.setTimeout(() => { copy.textContent = "Copy"; }, 2200);
    } catch {
      const range = document.createRange();
      range.selectNodeContents(document.getElementById("citation-text"));
      const selection = window.getSelection();
      selection.removeAllRanges();
      selection.addRange(range);
      status.textContent = "BibTeX selected. Use your browser’s Copy command.";
    }
  });

  // No background autoplay or third-party requests.
  document.addEventListener("visibilitychange", () => {
    if (document.hidden) video.pause();
  });

  // Mark the section under the sticky navigation as current.
  const navLinks = [...document.querySelectorAll(".nav-links a")];
  const sections = navLinks.map(link => document.getElementById(link.hash.slice(1))).filter(Boolean);
  let lastActive;
  function markCurrentSection() {
    const navBottom = document.querySelector(".section-nav").getBoundingClientRect().bottom;
    let current = null;
    for (const section of sections) {
      if (section.getBoundingClientRect().top - navBottom <= 80) current = section;
    }
    // At the end of the page, the last section is current even if it is short.
    if (window.innerHeight + window.scrollY >= document.documentElement.scrollHeight - 2) current = sections.at(-1);
    navLinks.forEach(link => {
      if (current && link.hash === `#${current.id}`) link.setAttribute("aria-current", "location");
      else link.removeAttribute("aria-current");
    });
    const active = navLinks.find(link => link.hasAttribute("aria-current"));
    if (active === lastActive) return;
    lastActive = active;
    const strip = active?.parentElement;
    // On narrow screens the link strip scrolls; keep the current link in view.
    if (active && strip.scrollWidth > strip.clientWidth) {
      const offset = active.offsetLeft - (strip.clientWidth - active.offsetWidth) / 2;
      strip.scrollTo({ left: offset, behavior: "auto" });
    }
  }
  let navFrame = 0;
  window.addEventListener("scroll", () => {
    if (navFrame) return;
    navFrame = window.requestAnimationFrame(() => { navFrame = 0; markCurrentSection(); });
  }, { passive: true });
  window.addEventListener("resize", markCurrentSection);
  markCurrentSection();
})();
