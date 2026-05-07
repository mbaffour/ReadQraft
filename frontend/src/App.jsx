import React, { useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import { Activity, Archive, Beaker, CheckCircle2, Download, FileDown, FolderOpen, Play, Settings, UploadCloud, Wrench } from "lucide-react";
import { api, apiBase } from "./api/client";
import "./styles/main.css";

const defaultOptions = {
  mode: "simple",
  trimming_engine: "fastp",
  phred_quality_threshold: 20,
  minimum_read_length: 50,
  adapter_sequence: "",
  auto_detect_adapters: true,
  poly_g_trimming: true,
  poly_x_trimming: false,
  threads: Math.max(1, Math.min(8, navigator.hardwareConcurrency || 4)),
  keep_intermediate_files: true,
  generate_methods_text: true,
  generate_checksums: true,
  show_command_preview: false
};

function Term({ term, help }) {
  return (
    <span>
      {term} <span className="bracket">[{help}]</span>
    </span>
  );
}

function App() {
  const [backend, setBackend] = useState({ status: "Starting backend", health: null, tools: null, error: null });
  const [projectId, setProjectId] = useState(null);
  const [upload, setUpload] = useState(null);
  const [mode, setMode] = useState("simple");
  const [options, setOptions] = useState(defaultOptions);
  const [job, setJob] = useState(null);
  const [events, setEvents] = useState([]);
  const [results, setResults] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    let stopped = false;
    async function poll() {
      try {
        const [health, tools] = await Promise.all([api.health(), api.tools()]);
        if (!stopped) setBackend({ status: tools.required_missing?.length ? "Tool check failed" : "Connected", health, tools, error: null });
      } catch (err) {
        if (!stopped) setBackend({ status: "Backend not available", health: null, tools: null, error: err.message });
        setTimeout(poll, 1200);
      }
    }
    poll();
    return () => {
      stopped = true;
    };
  }, []);

  async function ensureProject() {
    if (projectId) return projectId;
    const created = await api.createProject();
    setProjectId(created.project_id);
    return created.project_id;
  }

  async function handleFiles(files) {
    setError(null);
    const pid = await ensureProject();
    const response = await api.uploadFiles(pid, files);
    setUpload(response);
  }

  async function runAnalysis() {
    setError(null);
    setResults(null);
    setEvents([]);
    const response = await api.run(projectId, { ...options, mode });
    setJob(response);
    const source = new EventSource(`${apiBase()}/api/jobs/${response.job_id}/events`);
    source.onmessage = async (message) => {
      const event = JSON.parse(message.data);
      setEvents((current) => [...current, event]);
      if (["complete", "failed", "cancelled"].includes(event.status)) {
        source.close();
        if (event.status === "complete") {
          setResults(await api.results(projectId));
        }
      }
    };
    source.onerror = () => source.close();
  }

  const progress = events.at(-1)?.progress || 0;
  const canRun = upload?.samples?.length && !upload.samples.some((sample) => sample.status === "missing-pair") && backend.status !== "Backend not available";
  const commandPreview = useMemo(() => {
    if (!upload?.samples?.length) return "Upload FASTQ files to preview the selected workflow.";
    return `fastqc raw reads -> fastp Q${options.phred_quality_threshold}, minimum ${options.minimum_read_length} bp -> FastQC trimmed reads -> MultiQC -> reproducibility ZIP`;
  }, [upload, options]);

  return (
    <main className="app-shell">
      <section className="hero">
        <div>
          <div className="eyebrow"><Beaker size={16} /> Desktop FASTQ QC and trimming</div>
          <h1>ReadQraft</h1>
          <p>FASTQ QC and trimming without terminal fear.</p>
        </div>
        <div className={`status ${backend.status === "Connected" ? "ok" : backend.status === "Tool check failed" ? "warn" : "bad"}`}>
          <Activity size={18} />
          <div>
            <strong>{backend.status}</strong>
            <span>{backend.health ? `Local API ${backend.health.version} on 127.0.0.1` : backend.error || "Waiting for the local backend."}</span>
          </div>
        </div>
      </section>

      <section className="quick-actions">
        <button onClick={() => document.getElementById("fastq-picker").click()}><UploadCloud size={18} /> New analysis</button>
        <button disabled><FolderOpen size={18} /> Open previous analysis</button>
        <button disabled><FileDown size={18} /> View example workflow</button>
        <button><Settings size={18} /> Settings</button>
      </section>

      {backend.tools?.required_missing?.length ? (
        <section className="panel warning">
          <h2><Wrench size={18} /> Tool setup</h2>
          <p>Required tools were not found <span className="bracket">[FastQC, fastp, and MultiQC must be available for real analyses]</span>. Development mock mode can demonstrate the workflow, but publication analyses require real tools.</p>
          <div className="tool-grid">
            {backend.tools.tools.map((tool) => (
              <div className="tool" key={tool.name}>
                <strong>{tool.name}</strong>
                <span>{tool.available ? tool.version || "available" : tool.message}</span>
              </div>
            ))}
          </div>
        </section>
      ) : null}

      <section className="grid">
        <div className="panel">
          <h2><UploadCloud size={18} /> Select reads</h2>
          <input id="fastq-picker" type="file" multiple accept=".fastq,.fq,.fastq.gz,.fq.gz" onChange={(event) => handleFiles(event.target.files)} hidden />
          <div className="dropzone" onDragOver={(event) => event.preventDefault()} onDrop={(event) => { event.preventDefault(); handleFiles(event.dataTransfer.files); }}>
            <UploadCloud size={34} />
            <strong><Term term="FASTQ files" help="raw sequencing read files" /></strong>
            <span>Drag files here or choose FASTQ/FASTQ.gz files from your computer.</span>
            <button onClick={() => document.getElementById("fastq-picker").click()}>Choose files</button>
          </div>
          {upload ? <SampleTable upload={upload} /> : null}
        </div>

        <div className="panel">
          <h2>Workflow setup</h2>
          <div className="tabs">
            <button className={mode === "simple" ? "active" : ""} onClick={() => setMode("simple")}>Simple Mode</button>
            <button className={mode === "advanced" ? "active" : ""} onClick={() => setMode("advanced")}>Advanced Mode</button>
          </div>
          <div className="preset-row">
            {["Illumina short-read default [recommended for most short-read datasets]", "Conservative trimming [keeps more reads]", "Strict trimming [removes more low-quality sequence]", "Adapter-focused cleanup [prioritizes adapter removal]"].map((preset) => <button className="preset" key={preset}>{preset}</button>)}
          </div>
          <Options mode={mode} options={options} setOptions={setOptions} />
          <div className="preview">
            <strong>Recommended workflow summary</strong>
            <span>{commandPreview}</span>
          </div>
          <button className="run" disabled={!canRun} onClick={runAnalysis}><Play size={18} /> Run</button>
        </div>
      </section>

      <section className="panel">
        <h2><Activity size={18} /> Progress</h2>
        <div className="progress"><span style={{ width: `${progress}%` }} /></div>
        <div className="steps">
          {["Checking FASTQ integrity [making sure files look valid]", "Detecting read pairing [matching R1 and R2 files]", "Running raw FastQC [quality check before trimming]", "Running fastp [adapter and quality trimming]", "Running post-trim FastQC [quality check after trimming]", "Running MultiQC [combining reports]", "Generating reproducibility package [saving logs, commands, versions, and checksums]", "Complete"].map((step) => (
            <div className={events.some((event) => step.startsWith(event.step)) ? "done" : ""} key={step}><CheckCircle2 size={16} /> {step}</div>
          ))}
        </div>
        <details>
          <summary>View technical log</summary>
          <pre>{events.map((event) => `[${event.level}] ${event.step}: ${event.message}`).join("\n")}</pre>
        </details>
      </section>

      {results ? <Results results={results} /> : null}
      {error ? <div className="toast">{error}</div> : null}
    </main>
  );
}

function SampleTable({ upload }) {
  return (
    <table>
      <thead><tr><th>Sample</th><th>R1 file</th><th>R2 file</th><th>Status</th></tr></thead>
      <tbody>
        {upload.samples.map((sample) => (
          <tr key={sample.sample_id}>
            <td>{sample.sample_id}</td>
            <td>{sample.r1_file || "-"}</td>
            <td>{sample.r2_file || "-"}</td>
            <td><span className={sample.status === "missing-pair" ? "pill bad" : "pill ok"}>{sample.status}</span></td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function Options({ mode, options, setOptions }) {
  const update = (key, value) => setOptions((current) => ({ ...current, [key]: value }));
  return (
    <div className="options">
      {mode === "advanced" ? (
        <label><Term term="Trimming engine" help="software used to clean reads" /><select value={options.trimming_engine} onChange={(e) => update("trimming_engine", e.target.value)}><option>fastp</option><option>Cutadapt</option><option>Trimmomatic</option></select></label>
      ) : null}
      <label><Term term="Phred quality threshold" help="base-call confidence cutoff" /><input type="number" value={options.phred_quality_threshold} onChange={(e) => update("phred_quality_threshold", Number(e.target.value))} /></label>
      <label><Term term="Minimum read length" help="shortest read kept after trimming" /><input type="number" value={options.minimum_read_length} onChange={(e) => update("minimum_read_length", Number(e.target.value))} /></label>
      {mode === "advanced" ? (
        <>
          <label><Term term="Adapter sequence" help="known adapter sequence to remove" /><input value={options.adapter_sequence} onChange={(e) => update("adapter_sequence", e.target.value)} /></label>
          <label><Term term="Thread count" help="number of CPU cores used" /><input type="number" value={options.threads} onChange={(e) => update("threads", Number(e.target.value))} /></label>
          {["auto_detect_adapters", "poly_g_trimming", "poly_x_trimming", "keep_intermediate_files", "generate_methods_text", "generate_checksums", "show_command_preview"].map((key) => (
            <label className="check" key={key}><input type="checkbox" checked={options[key]} onChange={(e) => update(key, e.target.checked)} /> {key.replaceAll("_", " ")}</label>
          ))}
        </>
      ) : null}
    </div>
  );
}

function Results({ results }) {
  return (
    <section className="panel results">
      <h2><Archive size={18} /> Results</h2>
      <table>
        <thead><tr><th>Sample</th><th>Reads before trimming</th><th>Reads after trimming</th><th>Read retention percentage</th></tr></thead>
        <tbody>{results.samples.map((sample) => <tr key={sample.sample_id}><td>{sample.sample_id}</td><td>{sample.reads_before ?? "not parsed"}</td><td>{sample.reads_after ?? "not parsed"}</td><td>{sample.retention_percent ?? "not parsed"}</td></tr>)}</tbody>
      </table>
      <div className="downloads">
        <a href={`${apiBase()}${results.downloads.reproducibility_zip}`}><Download size={18} /> Download full reproducibility ZIP</a>
        <a href={`${apiBase()}${results.downloads.methods_text}`}><FileDown size={18} /> Download methods text</a>
        <a href={`${apiBase()}${results.downloads.command_log}`}><FileDown size={18} /> Download command log</a>
        <a href={`${apiBase()}${results.downloads.version_log}`}><FileDown size={18} /> Download version log</a>
      </div>
      <h3>Methods text</h3>
      <p className="methods">{results.methods_text}</p>
      <h3>Report links</h3>
      <div className="downloads">{results.reports.map((report) => <a key={report.url} href={`${apiBase()}${report.url}`}>{report.name}</a>)}</div>
    </section>
  );
}

createRoot(document.getElementById("root")).render(<App />);
