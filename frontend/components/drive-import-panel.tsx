"use client";

import { useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";

type RosterStudent = { id: string; name: string; identifier: string };
type DriveItem = {
  folder_id: string;
  folder_name: string;
  student_id: string | null;
  pages: { file_id: string; name: string; mime_type: string }[];
  status: string;
  error: string | null;
};

declare global {
  interface Window {
    gapi?: any;
    google?: any;
  }
}

const clientId = process.env.NEXT_PUBLIC_GOOGLE_DRIVE_CLIENT_ID;
const apiKey = process.env.NEXT_PUBLIC_GOOGLE_DRIVE_API_KEY;
const appId = process.env.NEXT_PUBLIC_GOOGLE_DRIVE_APP_ID;

function loadScript(src: string) {
  return new Promise<void>((resolve, reject) => {
    const existing = document.querySelector(`script[src="${src}"]`);
    if (existing) {
      resolve();
      return;
    }
    const script = document.createElement("script");
    script.src = src;
    script.async = true;
    script.onload = () => resolve();
    script.onerror = () => reject(new Error("Google Drive could not be loaded."));
    document.head.appendChild(script);
  });
}

function loadPickerApi() {
  return new Promise<void>((resolve, reject) => {
    if (!window.gapi?.load) {
      reject(new Error("Google Picker is unavailable. Refresh the page and try again."));
      return;
    }
    let settled = false;
    const timeout = window.setTimeout(() => {
      if (!settled) {
        settled = true;
        reject(new Error("Google Picker took too long to load."));
      }
    }, 10000);
    window.gapi.load("picker", () => {
      if (settled) return;
      settled = true;
      window.clearTimeout(timeout);
      resolve();
    });
  });
}

export function DriveImportPanel({ examId, roster }: { examId: string; roster: RosterStudent[] }) {
  const [open, setOpen] = useState(false);
  const [token, setToken] = useState("");
  const [batchId, setBatchId] = useState("");
  const [items, setItems] = useState<DriveItem[]>([]);
  const [assignments, setAssignments] = useState<Record<string, string>>({});
  const [status, setStatus] = useState("");
  const [error, setError] = useState("");
  const pickerRef = useRef<any>(null);

  useEffect(() => {
    if (!open || !clientId) return;
    void loadScript("https://accounts.google.com/gsi/client").catch((reason) => setError(reason instanceof Error ? reason.message : "Google Drive could not be loaded."));
  }, [open]);

  async function chooseFolder() {
    setError("");
    setStatus("Opening Google Drive...");
    if (!clientId || !apiKey || !appId) {
      setError("Google Drive Picker is not fully configured. Add the client ID, API key, and project number to the frontend deployment.");
      setStatus("");
      return;
    }
    try {
      await Promise.all([
        loadScript("https://apis.google.com/js/api.js"),
        loadScript("https://accounts.google.com/gsi/client"),
      ]);
      await loadPickerApi();
      const accessToken = await new Promise<string>((resolve, reject) => {
        const tokenClient = window.google.accounts.oauth2.initTokenClient({
          client_id: clientId,
          scope: "https://www.googleapis.com/auth/drive.file",
          callback: (response: any) => response.error ? reject(new Error("Google Drive authorization was not granted.")) : resolve(response.access_token),
        });
        tokenClient.requestAccessToken({ prompt: "consent" });
      });
      setToken(accessToken);
      const view = new window.google.picker.DocsView()
        .setIncludeFolders(true)
        .setSelectFolderEnabled(true);
      const picker = new window.google.picker.PickerBuilder()
        .setDeveloperKey(apiKey)
        .setAppId(appId)
        .setOAuthToken(accessToken)
        .setOrigin(window.location.origin)
        .setTitle("Choose the student papers folder")
        .addView(view)
        .setCallback((data: any) => {
          const action = data.action ?? data[window.google.picker.Response.ACTION];
          if (action === window.google.picker.Action.PICKED) {
            const folder = data.docs?.[0];
            const folderId = folder?.id ?? folder?.[window.google.picker.Document.ID];
            picker.setVisible(false);
            pickerRef.current = null;
            if (folderId) void preview(folderId, accessToken);
          } else if (action === window.google.picker.Action.CANCEL || action === window.google.picker.Action.ERROR) {
            picker.setVisible(false);
            pickerRef.current = null;
            setStatus("");
            if (action === window.google.picker.Action.ERROR) setError("Google Drive could not open the folder picker. Check the Picker API key and project number.");
          }
        })
        .build();
      pickerRef.current = picker;
      picker.setVisible(true);
      setStatus("");
    } catch (reason) {
      pickerRef.current?.setVisible(false);
      pickerRef.current = null;
      setStatus("");
      setError(reason instanceof Error ? reason.message : "Google Drive could not be opened.");
    }
  }

  function closeImportPanel() {
    pickerRef.current?.setVisible(false);
    pickerRef.current = null;
    setOpen(false);
    setStatus("");
    setError("");
  }

  async function preview(folderId: string, accessToken: string) {
    setStatus("Scanning student folders...");
    try {
      const result = await api.post<{ id: string; items: DriveItem[] }>(`/api/exams/${examId}/imports/drive/preview`, { root_folder_id: folderId, access_token: accessToken });
      setBatchId(result.id);
      setItems(result.items);
      setAssignments(result.items.reduce<Record<string, string>>((current, item) => {
        if (item.student_id) current[item.folder_id] = item.student_id;
        return current;
      }, {}));
      setStatus("Review the matches, then import the confirmed papers.");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "The Drive folder could not be scanned.");
      setStatus("");
    }
  }

  async function commit() {
    setStatus("Importing papers...");
    try {
      await api.post(`/api/imports/${batchId}/commit`, { access_token: token, assignments });
      setStatus("Papers imported. Processing has started.");
      setItems((current) => current.map((item) => ({ ...item, status: "imported" })));
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "The Drive papers could not be imported.");
      setStatus("");
    }
  }

  return (
    <section className="surface-lined mt-5 p-5">
      <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-center">
        <div>
          <h3 className="font-serif text-2xl font-semibold">Import from Google Drive</h3>
          <p className="mt-1 text-sm text-[var(--ink-muted)]">Choose a folder containing one folder per student and numbered image pages.</p>
        </div>
        <button type="button" className="button-secondary" onClick={() => { setOpen(true); void chooseFolder(); }}>Choose Drive folder</button>
      </div>
      {open && <div className="mt-4 rounded-lg bg-[var(--surface-muted)] p-4">
        <div className="mb-3 flex justify-end">
          <button type="button" className="button-quiet px-2 py-1 text-xs" onClick={closeImportPanel}>Close</button>
        </div>
        {error && <p role="alert" className="text-sm text-[var(--review)]">{error}</p>}
        {status && <p className="text-sm text-[var(--ink-muted)]">{status}</p>}
        {!items.length && !error && <p className="text-xs text-[var(--ink-muted)]">Expected structure: `Students / Student Name / 1.jpeg, 2.jpeg`.</p>}
        {items.length > 0 && <>
          <div className="divide-y divide-[var(--line)] rounded-lg border border-[var(--line)] bg-[var(--surface)]">
            {items.map((item) => <div key={item.folder_id} className="flex flex-col gap-2 p-3 sm:flex-row sm:items-center sm:justify-between">
              <div><strong>{item.folder_name}</strong><p className="text-xs text-[var(--ink-muted)]">{item.pages.length} pages · {item.error ?? item.status}</p></div>
              <select aria-label={`Assign ${item.folder_name}`} value={assignments[item.folder_id] ?? ""} onChange={(event) => setAssignments((current) => ({ ...current, [item.folder_id]: event.target.value }))} className="input sm:max-w-xs">
                <option value="">Choose student</option>
                {roster.map((student) => <option key={student.id} value={student.id}>{student.name} ({student.identifier})</option>)}
              </select>
            </div>)}
          </div>
          <button type="button" className="button-primary mt-4" disabled={!batchId || items.some((item) => !assignments[item.folder_id] || !item.pages.length)} onClick={() => void commit()}>Import confirmed papers</button>
        </>}
      </div>}
    </section>
  );
}
