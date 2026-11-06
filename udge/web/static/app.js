document.addEventListener("DOMContentLoaded", () => {
  const templateInput = document.getElementById("templateFile");
  const templateName = document.getElementById("templateName");
  const sourcesInput = document.getElementById("sourceFiles");
  const sourcesSummary = document.getElementById("sourcesSummary");
  const selectedSourcesList = document.getElementById("selectedSourcesList");
  const form = document.getElementById("generationForm");
  const btnSubmit = document.getElementById("btnSubmit");
  const statusBox = document.getElementById("statusBox");
  const deliverablesPanel = document.getElementById("deliverablesPanel");
  const downloadsGrid = document.getElementById("downloadsGrid");
  const qaMetrics = document.getElementById("qaMetrics");
  const qaDetails = document.getElementById("qaDetails");
  const stepper = document.getElementById("pipelineStepper");

  // File selection display
  templateInput.addEventListener("change", () => {
    if (templateInput.files.length > 0) {
      templateName.textContent = templateInput.files[0].name;
    }
  });

  sourcesInput.addEventListener("change", () => {
    selectedSourcesList.innerHTML = "";
    const files = Array.from(sourcesInput.files);
    if (files.length > 0) {
      sourcesSummary.textContent = `${files.length} document(s) selected`;
      files.forEach(f => {
        const li = document.createElement("li");
        li.innerHTML = `<span>📄</span> ${f.name} <span style="font-size:0.7em;opacity:0.6;">(${(f.size/1024).toFixed(1)} KB)</span>`;
        selectedSourcesList.appendChild(li);
      });
    }
  });

  // Stage order mapping
  const stageOrder = [
    "ingesting",
    "analyzing_template",
    "mapping_content",
    "generating_sections",
    "editorial_review",
    "rendering",
    "validating"
  ];

  function updateStepper(currentStage) {
    const currentIdx = stageOrder.indexOf(currentStage);
    const steps = stepper.querySelectorAll(".step-item");
    steps.forEach((step, idx) => {
      step.classList.remove("active", "completed");
      if (idx < currentIdx) {
        step.classList.add("completed");
      } else if (idx === currentIdx) {
        step.classList.add("active");
      }
    });
  }

  form.addEventListener("submit", async (e) => {
    e.preventDefault();

    if (!templateInput.files.length) {
      alert("Please select a template file (.md, .txt, .docx, .pdf).");
      return;
    }
    if (!sourcesInput.files.length) {
      alert("Please select at least one reference document.");
      return;
    }

    const formData = new FormData();
    formData.append("template", templateInput.files[0]);

    for (let f of sourcesInput.files) {
      formData.append("sources", f);
    }

    const selectedFmts = Array.from(document.querySelectorAll("input[name='fmt']:checked")).map(c => c.value);
    formData.append("formats", selectedFmts.join(","));
    formData.append("llm", document.getElementById("llmProvider").value);

    // Disable button & show spinner
    btnSubmit.disabled = true;
    deliverablesPanel.style.display = "none";
    statusBox.innerHTML = `
      <div class="status-active-spinner">
        <div class="spinner"></div>
        <h3>Synthesizing Document Pipeline...</h3>
        <p id="liveStatusText">Submitting ingestion payload to server...</p>
      </div>
    `;

    try {
      const resp = await fetch("/api/jobs", {
        method: "POST",
        body: formData
      });

      if (!resp.ok) {
        throw new Error(`Job submission failed with status ${resp.status}`);
      }

      const data = await resp.json();
      const jobId = data.job_id;

      // Start polling
      pollJobStatus(jobId);
    } catch (err) {
      statusBox.innerHTML = `<div style="color:var(--accent-rose);"><h3>Generation Error</h3><p>${err.message}</p></div>`;
      btnSubmit.disabled = false;
    }
  });

  async function pollJobStatus(jobId) {
    const statusText = document.getElementById("liveStatusText");
    const interval = setInterval(async () => {
      try {
        const resp = await fetch(`/api/jobs/${jobId}`);
        if (!resp.ok) return;

        const job = await resp.json();
        const stage = job.status;

        updateStepper(stage);

        if (statusText) {
          statusText.textContent = `Stage: ${stage.replace("_", " ").toUpperCase()}`;
        }

        if (stage === "completed") {
          clearInterval(interval);
          btnSubmit.disabled = false;
          renderCompletion(job);
        } else if (stage === "failed") {
          clearInterval(interval);
          btnSubmit.disabled = false;
          statusBox.innerHTML = `
            <div style="color:var(--accent-rose);">
              <h3>Pipeline Failure</h3>
              <p>${job.error_message || "An unknown error occurred during generation."}</p>
            </div>
          `;
        }
      } catch (e) {
        console.error("Polling error:", e);
      }
    }, 1000);
  }

  function renderCompletion(job) {
    statusBox.innerHTML = `
      <div style="color:var(--accent-emerald);">
        <div style="font-size:2.5rem;margin-bottom:0.5rem;">🎉</div>
        <h3>Synthesis & QA Completed Successfully!</h3>
        <p>Your document was rendered via LibreOffice and verified against template criteria.</p>
      </div>
    `;

    // Render downloads
    downloadsGrid.innerHTML = "";
    for (let [fmt, path] of Object.entries(job.output_files)) {
      const a = document.createElement("a");
      a.className = "btn-download";
      a.href = `/api/jobs/${job.job_id}/download/${fmt}`;
      a.target = "_blank";
      a.innerHTML = `<span>📥</span> Download .${fmt.toUpperCase()}`;
      downloadsGrid.appendChild(a);
    }

    // Validation report download
    const repLink = document.createElement("a");
    repLink.className = "btn-download";
    repLink.href = `/api/jobs/${job.job_id}/download/report`;
    repLink.target = "_blank";
    repLink.innerHTML = `<span>📋</span> QA Report (.MD)`;
    downloadsGrid.appendChild(repLink);

    // Render QA metrics
    if (job.validation_report) {
      const rep = job.validation_report;
      qaMetrics.innerHTML = `
        <div class="qa-metric-card">
          <div class="qa-val" style="color: ${rep.passed ? 'var(--accent-emerald)' : 'var(--accent-rose)'};">${rep.passed ? 'PASSED' : 'FLAGGED'}</div>
          <div class="qa-lbl">QA Status</div>
        </div>
        <div class="qa-metric-card">
          <div class="qa-val" style="color: var(--accent-blue);">${rep.total_checks}</div>
          <div class="qa-lbl">Rules Checked</div>
        </div>
        <div class="qa-metric-card">
          <div class="qa-val" style="color: ${rep.warnings.length ? 'var(--accent-amber)' : 'var(--text-muted)'};">${rep.warnings.length}</div>
          <div class="qa-lbl">Warnings</div>
        </div>
        <div class="qa-metric-card">
          <div class="qa-val" style="color: var(--accent-cyan);">${rep.info.length}</div>
          <div class="qa-lbl">Gaps Tracked</div>
        </div>
      `;

      qaDetails.textContent = rep.summary + "\n\n" +
        (rep.warnings.length ? "Warnings:\n" + rep.warnings.map(w => `• [${w.code}] ${w.message}`).join("\n") + "\n\n" : "") +
        (rep.info.length ? "Notices & Gaps:\n" + rep.info.map(i => `• [${i.code}] ${i.message}`).join("\n") : "All required content verified.");
    }

    deliverablesPanel.style.display = "block";
  }
});
