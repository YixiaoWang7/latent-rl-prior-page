"use strict";

// Interactive contact-force explorer (paper Figure 9). The static vector figure
// #contact-fallback stays visible until the data loads and validates.
(() => {
  const number = new Intl.NumberFormat("en-US");
  const svgNS = "http://www.w3.org/2000/svg";
  // Same colors as --ours and --scratch in styles.css; "ours" is orange as in the paper's figures.
  const priorColor = "#cf5f28";
  const scratchColor = "#69767b";

  function append(parent, tag, attributes = {}, text) {
    const node = document.createElementNS(svgNS, tag);
    for (const [key, value] of Object.entries(attributes)) node.setAttribute(key, value);
    if (text !== undefined) node.textContent = text;
    parent.append(node);
    return node;
  }

  // Arrow-key navigation for a group of toggle buttons.
  function arrowNavigation(buttons, select) {
    buttons.forEach((button, index) => {
      button.addEventListener("keydown", (event) => {
        let next;
        if (event.key === "ArrowRight" || event.key === "ArrowDown") next = (index + 1) % buttons.length;
        else if (event.key === "ArrowLeft" || event.key === "ArrowUp") next = (index + buttons.length - 1) % buttons.length;
        else if (event.key === "Home") next = 0;
        else if (event.key === "End") next = buttons.length - 1;
        else return;
        event.preventDefault();
        select(buttons[next], next);
        buttons[next].focus();
      });
    });
  }

  async function setupContact() {
    const root = document.getElementById("contact-explorer");
    const response = await fetch("./assets/data/contact-probes.json");
    if (!response.ok) throw new Error(`Contact data unavailable (${response.status})`);
    const data = await response.json();
    // Validate before hiding the independently readable vector fallback.
    for (const target of Object.values(data.targets)) {
      for (const budget of data.budgets) {
        for (const model of ["prior", "scratch"]) {
          const values = target.series[budget][model].mean;
          if (values.length !== 8 || values.some(value => !Number.isFinite(value))) throw new Error("Invalid contact data");
        }
      }
    }
    const chart = document.getElementById("contact-chart");
    const budget = document.getElementById("force-budget");
    const forceButtons = [...root.querySelectorAll("[data-force]")];
    const layerGroup = document.getElementById("layer-buttons");
    const domains = {
      grasp: { min: 9.4, max: 12.6, ticks: [9.5, 10, 10.5, 11, 11.5, 12, 12.5] },
      normal: { min: 3.75, max: 4.7, ticks: [3.8, 4, 4.2, 4.4, 4.6] },
      tangential: { min: 3.6, max: 4.08, ticks: [3.6, 3.7, 3.8, 3.9, 4] },
      vector: { min: 3.7, max: 4.5, ticks: [3.7, 3.9, 4.1, 4.3, 4.5] },
    };
    let force = "grasp", count = 200, layer = 3;
    let compact = window.matchMedia("(max-width: 760px)").matches;
    let plotLeft, plotRight, viewWidth;
    let graphic, highlight, priorDot, scratchDot, priorValues, scratchValues, x, y;
    const layerButtons = data.layers.map((name, index) => {
      const button = document.createElement("button");
      button.type = "button";
      button.textContent = name;
      button.setAttribute("aria-label", `Inspect decoder layer ${index + 1}`);
      button.addEventListener("click", () => selectLayer(index));
      layerGroup.append(button);
      return button;
    });

    function selectLayer(index) {
      layer = index;
      layerButtons.forEach((button, i) => button.setAttribute("aria-pressed", String(i === index)));
      const prior = priorValues[index], scratch = scratchValues[index];
      highlight.setAttribute("x1", x(index));
      highlight.setAttribute("x2", x(index));
      priorDot.setAttribute("cx", x(index));
      priorDot.setAttribute("cy", y(prior));
      scratchDot.setAttribute("cx", x(index));
      scratchDot.setAttribute("cy", y(scratch));
      document.getElementById("force-layer-name").textContent = `Layer ${index + 1}`;
      document.getElementById("force-prior-value").textContent = prior.toFixed(2);
      document.getElementById("force-scratch-value").textContent = scratch.toFixed(2);
      const difference = (scratch - prior) / scratch * 100;
      const insight = document.getElementById("force-insight");
      insight.replaceChildren();
      const strong = document.createElement("strong");
      strong.textContent = `${difference.toFixed(1)}% lower error`;
      insight.append(strong, ` with the RL prior at layer ${index + 1}.`);
      chart.setAttribute("aria-label", `${data.targets[force].name}, ${count} visual demonstrations. At layer ${index + 1}, RMSE is ${prior.toFixed(2)} newtons with the RL prior and ${scratch.toFixed(2)} with the scratch decoder. Lower is better.`);
    }

    function render() {
      const target = data.targets[force];
      priorValues = target.series[count].prior.mean;
      scratchValues = target.series[count].scratch.mean;
      forceButtons.forEach(button => button.setAttribute("aria-pressed", String(button.dataset.force === force)));
      document.getElementById("force-definition").textContent = target.description;
      document.getElementById("force-budget-value").textContent = number.format(count);
      budget.setAttribute("aria-valuetext", `${number.format(count)} demonstrations`);
      chart.replaceChildren();
      viewWidth = compact ? 440 : 790;
      graphic = append(chart, "svg", { viewBox: `0 0 ${viewWidth} ${compact ? 350 : 390}`, "aria-hidden": "true" });
      const left = compact ? 50 : 64, right = compact ? 423 : 662, top = 34, bottom = compact ? 292 : 332;
      plotLeft = left;
      plotRight = right;
      const domain = domains[force];
      x = index => left + index * (right - left) / 7;
      y = value => bottom - (value - domain.min) / (domain.max - domain.min) * (bottom - top);
      append(graphic, "text", { x: left - 46, y: 17, class: "chart-axis-title" }, "Probe RMSE (N)");
      domain.ticks.forEach(tick => {
        append(graphic, "line", { x1: left, x2: right, y1: y(tick), y2: y(tick), class: "chart-gridline" });
        append(graphic, "text", { x: left - 12, y: y(tick) + 5, "text-anchor": "end", class: "chart-tick" }, tick.toFixed(1));
      });
      data.layers.forEach((name, i) => append(graphic, "text", { x: x(i), y: bottom + 28, "text-anchor": "middle", class: "chart-tick" }, name));
      append(graphic, "text", { x: (left + right) / 2, y: bottom + 55, "text-anchor": "middle", class: "chart-axis-title" }, "Action-decoder layer");
      highlight = append(graphic, "line", { y1: top, y2: bottom, class: "chart-inspection-line" });
      for (const [values, color, dashed] of [[scratchValues, scratchColor, true], [priorValues, priorColor, false]]) {
        append(graphic, "path", {
          d: values.map((value, i) => `${i ? "L" : "M"}${x(i)},${y(value)}`).join(" "),
          fill: "none", stroke: color, "stroke-width": 3.5, ...(dashed ? { "stroke-dasharray": "8 6" } : {}),
        });
        values.forEach((value, i) => append(graphic, "circle", {
          cx: x(i), cy: y(value), r: 4, fill: color, stroke: "white", "stroke-width": 1.5,
        }));
        if (!compact) {
          const label = append(graphic, "text", { x: right + 14, y: y(values[7]) - 6, class: "chart-end-label", fill: color });
          append(label, "tspan", { x: right + 14 }, dashed ? "Scratch" : "RL prior");
          append(label, "tspan", { x: right + 14, dy: 19 }, `${values[7].toFixed(2)} N`);
        }
      }
      scratchDot = append(graphic, "circle", { r: 7, fill: scratchColor, stroke: "white", "stroke-width": 2.5 });
      priorDot = append(graphic, "circle", { r: 7, fill: priorColor, stroke: "white", "stroke-width": 2.5 });
      selectLayer(layer);
    }

    function inspectPointer(event) {
      if (!graphic) return;
      const bounds = graphic.getBoundingClientRect();
      const position = (event.clientX - bounds.left) / bounds.width * viewWidth;
      const next = Math.max(0, Math.min(7, Math.round((position - plotLeft) / (plotRight - plotLeft) * 7)));
      if (next !== layer) selectLayer(next);
    }
    chart.addEventListener("pointerdown", inspectPointer);
    chart.addEventListener("pointermove", event => { if (event.pointerType === "mouse") inspectPointer(event); });
    forceButtons.forEach(button => button.addEventListener("click", () => { force = button.dataset.force; render(); }));
    arrowNavigation(forceButtons, button => { force = button.dataset.force; render(); });
    arrowNavigation(layerButtons, (_, index) => selectLayer(index));
    budget.addEventListener("input", () => { count = data.budgets[Number(budget.value)]; render(); });
    window.addEventListener("resize", () => {
      const next = window.matchMedia("(max-width: 760px)").matches;
      if (next !== compact) { compact = next; render(); }
    });
    render();
    root.hidden = false;
    document.getElementById("contact-fallback").hidden = true;
  }

  setupContact().catch(() => {
    // The full vector figure stays visible when data cannot load.
    document.getElementById("contact-explorer").hidden = true;
    document.getElementById("contact-fallback").hidden = false;
  });
})();
