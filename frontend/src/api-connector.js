/**
 * design.jobs — Frontend API connector
 *
 * Drop this into your HTML board to replace the static data
 * with live results from your FastAPI backend.
 *
 * Usage:
 *   const API = new DesignJobsAPI("https://your-api.railway.app");
 *   const { jobs, total } = await API.fetchJobs({ role: "ui", work: "remote" });
 */

const API_BASE = "http://localhost:8000"; // Change to your deployed URL

class DesignJobsAPI {
  constructor(base = API_BASE) {
    this.base = base;
  }

  async fetchJobs({
    q = "",
    role = "all",
    work = "all",
    region = "all",
    source = "all",
    sector = "all",
    experience = "all",
    sort = "newest",
    page = 1,
    perPage = 20,
    isNew,
    featured,
    salaryMin,
    salaryMax,
  } = {}) {
    const params = new URLSearchParams();
    if (q) params.set("q", q);
    if (role !== "all") params.set("role", role);
    if (work !== "all") params.set("work", work);
    if (region !== "all") params.set("region", region);
    if (source !== "all") params.set("source", source);
    if (sector !== "all") params.set("sector", sector);
    if (experience !== "all") params.set("experience", experience);
    if (isNew !== undefined) params.set("is_new", isNew);
    if (featured !== undefined) params.set("featured", featured);
    if (salaryMin) params.set("salary_min", salaryMin);
    if (salaryMax) params.set("salary_max", salaryMax);
    params.set("sort", sort);
    params.set("page", page);
    params.set("per_page", perPage);

    const res = await fetch(`${this.base}/jobs?${params}`);
    if (!res.ok) throw new Error(`API error: ${res.status}`);
    return res.json(); // { jobs, total, page, pages }
  }

  async fetchStats() {
    const res = await fetch(`${this.base}/stats`);
    return res.json();
    // { total_jobs, remote_jobs, new_today, india_jobs, active_sources }
  }

  async fetchSources() {
    const res = await fetch(`${this.base}/sources`);
    return res.json();
  }

  async fetchJob(id) {
    const res = await fetch(`${this.base}/jobs/${id}`);
    if (!res.ok) throw new Error("Job not found");
    return res.json();
  }
}

// ─── Example: Wire up the board ──────────────────────────────────────────────
// Replace the render() function in your board with this:

const api = new DesignJobsAPI(API_BASE);

async function loadAndRender(filters = {}) {
  const container = document.getElementById("jobs-container");
  container.innerHTML = '<div style="padding:40px;text-align:center;color:var(--color-text-tertiary)">Loading…</div>';

  try {
    // Load stats for header
    const stats = await api.fetchStats();
    document.getElementById("total-count").textContent = stats.total_jobs;
    document.getElementById("remote-count").textContent = stats.remote_jobs;
    document.getElementById("new-today").textContent = stats.new_today;

    // Load jobs
    const { jobs, total, pages } = await api.fetchJobs(filters);
    document.getElementById("filtered-count").textContent = total;

    if (jobs.length === 0) {
      container.innerHTML = '<div style="padding:40px;text-align:center;color:var(--color-text-tertiary)">No roles found. Try wider filters.</div>';
      return;
    }

    container.innerHTML = jobs.map(renderCard).join("");

    // Pagination
    const lb = document.getElementById("load-more-btn");
    lb.style.display = filters.page < pages ? "block" : "none";
  } catch (e) {
    container.innerHTML = `<div style="padding:40px;text-align:center;color:var(--color-text-danger)">Could not load jobs: ${e.message}</div>`;
  }
}

// Debounced live search
let searchTimer;
document.getElementById("search-input").addEventListener("input", (e) => {
  clearTimeout(searchTimer);
  searchTimer = setTimeout(() => loadAndRender({ q: e.target.value }), 350);
});

// Auto-refresh every 60 seconds
setInterval(() => loadAndRender(), 60000);

// Initial load
loadAndRender();
