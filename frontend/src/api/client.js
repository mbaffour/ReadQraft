const DEFAULT_API = "http://127.0.0.1:8765";

export function apiBase() {
  return window.readqraft?.apiBase || import.meta.env.VITE_READQRAFT_API || DEFAULT_API;
}

async function request(path, options = {}) {
  const response = await fetch(`${apiBase()}${path}`, options);
  if (!response.ok) {
    let detail = response.statusText;
    try {
      detail = (await response.json()).detail || detail;
    } catch {
      // keep status text
    }
    throw new Error(detail);
  }
  return response.json();
}

export const api = {
  health: () => request("/api/health"),
  tools: () => request("/api/tools"),
  createProject: () => request("/api/projects", { method: "POST" }),
  uploadFiles: async (projectId, files) => {
    const form = new FormData();
    Array.from(files).forEach((file) => form.append("files", file));
    return request(`/api/projects/${projectId}/files`, { method: "POST", body: form });
  },
  run: (projectId, options) =>
    request(`/api/projects/${projectId}/run`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(options)
    }),
  job: (jobId) => request(`/api/jobs/${jobId}`),
  results: (projectId) => request(`/api/projects/${projectId}/results`)
};
