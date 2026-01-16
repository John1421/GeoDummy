import { useState, useEffect, useRef } from "react";
import BaseMapSettings from "./BaseMapSettings";
import logo from "../assets/logo.png";
import WindowTemplate from "../TemplateModals/PopUpWindowModal";

const BUTTON_STYLE = "text-white font-semibold py-2 px-4 hover:opacity-80 transition";

type HeaderProps = {
  setBaseMapUrl: (url: string) => void;
  setBaseMapAttribution: (attribution: string) => void;
  enableHoverHighlight: boolean;
  setEnableHoverHighlight: (enabled: boolean) => void;
  enableClickPopup: boolean;
  setEnableClickPopup: (enabled: boolean) => void;
  onScriptsImported: () => void;
};

async function fetchExportAllScriptsZip(): Promise<Blob> {
  const response = await fetch("http://localhost:5050/scripts/export/all", {
    method: "GET",
  });

  if (!response.ok) {
    // Try to parse JSON error, otherwise fallback to text
    let details = "";
    try {
      const maybeJson = await response.json();
      details = JSON.stringify(maybeJson);
    } catch {
      try {
        details = await response.text();
      } catch {
        details = "";
      }
    }

    throw new Error(
      `Export failed (HTTP ${response.status}). ${details ? `Details: ${details}` : ""}`.trim()
    );
  }

  return await response.blob();
}

async function fetchExportAllLayersZip(): Promise<Blob> {
  const response = await fetch("http://localhost:5050/layers/export/all", {
    method: "GET",
  });

  if (!response.ok) {
    // Try to parse JSON error, otherwise fallback to text
    let details = "";
    try {
      const maybeJson = await response.json();
      details = JSON.stringify(maybeJson);
    } catch {
      try {
        details = await response.text();
      } catch {
        details = "";
      }
    }

    throw new Error(
      `Export failed (HTTP ${response.status}). ${details ? `Details: ${details}` : ""}`.trim()
    );
  }

  return await response.blob();
}

async function importScriptsZip(zipFile: File): Promise<{ imported_count: number; scripts: Array<{ script_id: string; metadata: unknown }> }> {
  const formData = new FormData();
  formData.append('file', zipFile);

  const response = await fetch("http://localhost:5050/scripts/import", {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    let details = "";
    try {
      const maybeJson = await response.json();
      details = maybeJson?.error?.description || JSON.stringify(maybeJson);
    } catch {
      try {
        details = await response.text();
      } catch {
        details = "";
      }
    }

    throw new Error(
      `Import failed (HTTP ${response.status}). ${details ? `Details: ${details}` : ""}`.trim()
    );
  }

  return await response.json();
}

function ensureZipExtension(name: string): string {
  const trimmed = name.trim();
  if (!trimmed) return "all_scripts_export.zip";
  return trimmed.toLowerCase().endsWith(".zip") ? trimmed : `${trimmed}.zip`;
}

async function saveBlobWithPicker(blob: Blob, suggestedName: string): Promise<void> {
  // Use the File System Access API (Chromium-based browsers)
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const anyWindow = window as any;

  if (typeof anyWindow.showSaveFilePicker !== "function") {
    throw new Error("File picker not supported");
  }

  const handle = await anyWindow.showSaveFilePicker({
    suggestedName,
    types: [
      {
        description: "ZIP archive",
        accept: { "application/zip": [".zip"] },
      },
    ],
  });

  const writable = await handle.createWritable();
  await writable.write(blob);
  await writable.close();
}

function downloadBlobFallback(blob: Blob, filename: string): void {
  // Browser download fallback: cannot guarantee folder selection programmatically
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

function Header({
  setBaseMapUrl,
  setBaseMapAttribution,
  enableHoverHighlight,
  setEnableHoverHighlight,
  enableClickPopup,
  setEnableClickPopup,
  onScriptsImported,
}: HeaderProps) {
  const [openBaseMapSet, setOpenBaseMapSet] = useState(false);

  // Settings dropdown
  const [openSettings, setOpenSettings] = useState(false);
  const settingsRef = useRef<HTMLDivElement>(null);

  // File dropdown
  const [openFileMenu, setOpenFileMenu] = useState(false);
  const fileRef = useRef<HTMLDivElement>(null);

  // Basemap dropdown
  const [openBasemapMenu, setOpenBasemapMenu] = useState(false);
  const basemapRef = useRef<HTMLDivElement>(null);

  // Export UX
  const [exporting, setExporting] = useState(false);
  const [exportErrorOpen, setExportErrorOpen] = useState(false);
  const [exportErrorMsg, setExportErrorMsg] = useState<string>("");

  const [exportingLayers, setExportingLayers] = useState(false);
  const [exportLayersErrorOpen, setExportLayersErrorOpen] = useState(false);
  const [exportLayersErrorMsg, setExportLayersErrorMsg] = useState<string>("");

  // Import UX
  const [importing, setImporting] = useState(false);
  const [importErrorOpen, setImportErrorOpen] = useState(false);
  const [importErrorMsg, setImportErrorMsg] = useState<string>("");
  const importFileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      const target = event.target as Node;

      if (openSettings && settingsRef.current && !settingsRef.current.contains(target)) {
        setOpenSettings(false);
      }
      if (openFileMenu && fileRef.current && !fileRef.current.contains(target)) {
        setOpenFileMenu(false);
      }
      if (openBasemapMenu && basemapRef.current && !basemapRef.current.contains(target)) {
        setOpenBasemapMenu(false);
      }
    };

    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [openSettings, openFileMenu, openBasemapMenu]);

  async function handleExportScripts() {
    setOpenFileMenu(false);
    setExporting(true);

    const defaultFilename = "all_scripts_export.zip";

    try {
      const zipBlob = await fetchExportAllScriptsZip();

      // Prefer save picker (folder + filename change in OS dialog)
      try {
        await saveBlobWithPicker(zipBlob, defaultFilename);
      } catch (pickerErr: unknown) {
        // If user cancels the picker, we must show the error modal
        // DOMException name commonly "AbortError"
        const maybeDomEx = pickerErr as { name?: string; message?: string };
        if (maybeDomEx?.name === "AbortError") {
          setExportErrorMsg("Exportação cancelada. O ficheiro não foi guardado.");
          setExportErrorOpen(true);
          return;
        }

        // If picker not supported, fall back to normal download
        // (cannot reliably detect user cancelling the Save As dialog in this fallback)
        const filename = ensureZipExtension(defaultFilename);
        downloadBlobFallback(zipBlob, filename);
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Erro desconhecido ao exportar scripts.";
      setExportErrorMsg(msg);
      setExportErrorOpen(true);
    } finally {
      setExporting(false);
    }
  }

  async function handleExportLayers() {
    setOpenFileMenu(false);
    setExportingLayers(true);

    const defaultFilename = "all_layers_export.zip";

    try {
      const zipBlob = await fetchExportAllLayersZip();

      // Prefer save picker (folder + filename change in OS dialog)
      try {
        await saveBlobWithPicker(zipBlob, defaultFilename);
      } catch (pickerErr: unknown) {
        // If user cancels the picker, we must show the error modal
        // DOMException name commonly "AbortError"
        const maybeDomEx = pickerErr as { name?: string; message?: string };
        if (maybeDomEx?.name === "AbortError") {
          setExportLayersErrorMsg("Export canceled. The file was not saved.");
          setExportLayersErrorOpen(true);
          return;
        }

        // If picker not supported, fall back to normal download
        // (cannot reliably detect user cancelling the Save As dialog in this fallback)
        const filename = ensureZipExtension(defaultFilename);
        downloadBlobFallback(zipBlob, filename);
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Unknown error exporting layers.";
      setExportLayersErrorMsg(msg);
      setExportLayersErrorOpen(true);
    } finally {
      setExportingLayers(false);
    }
  }

  function handleImportScriptsClick() {
    setOpenFileMenu(false);
    importFileInputRef.current?.click();
  }

  async function handleImportScriptsFile(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;

    // Validate file extension
    if (!file.name.toLowerCase().endsWith('.zip')) {
      setImportErrorMsg("Only .zip files are supported.");
      setImportErrorOpen(true);
      event.target.value = ''; // Reset input
      return;
    }

    setImporting(true);

    try {
      const result = await importScriptsZip(file);
      // Success - trigger script list refresh
      console.log(`Successfully imported ${result.imported_count} scripts`);
      onScriptsImported();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Unknown error importing scripts.";
      setImportErrorMsg(msg);
      setImportErrorOpen(true);
    } finally {
      setImporting(false);
      event.target.value = ''; // Reset input so same file can be selected again
    }
  }

  return (
    <div className="w-full bg-linear-to-r from-[#0D73A5] to-[#99E0B9] text-white px-4 py-2 flex items-center justify-between">
      <div className="flex gap-4 relative">
        {/* BASEMAP MENU */}
        <div className="relative" ref={basemapRef}>
          <button
            data-testid="edit-basemap-button"
            onClick={() => {
              setOpenBasemapMenu(!openBasemapMenu);
              setOpenFileMenu(false);
              setOpenSettings(false);
            }}
            onMouseDown={(e) => e.stopPropagation()}
            className={BUTTON_STYLE}
          >
            Settings
          </button>

          {openBasemapMenu && (
            <div className="absolute top-full left-0 mt-2 bg-white rounded-lg shadow-xl p-4 z-50 min-w-[250px]">
              <button
                onClick={() => {
                  setOpenBasemapMenu(false);
                  setOpenBaseMapSet(true);
                }}
                className="w-full text-left px-3 py-2 rounded-md text-gray-800 hover:bg-gray-100 mb-3"
              >
                Change basemap
              </button>

              <div className="border-t border-gray-200 pt-3 space-y-3">
                <div className="flex items-center gap-3">
                  <input
                    type="checkbox"
                    id="hover-highlight"
                    checked={enableHoverHighlight}
                    onChange={(e) => setEnableHoverHighlight(e.target.checked)}
                    className="w-4 h-4 cursor-pointer"
                  />
                  <label htmlFor="hover-highlight" className="text-gray-700 cursor-pointer">
                    Enable Hover Highlight
                  </label>
                </div>

                <div className="flex items-center gap-3">
                  <input
                    type="checkbox"
                    id="click-popup"
                    checked={enableClickPopup}
                    onChange={(e) => setEnableClickPopup(e.target.checked)}
                    className="w-4 h-4 cursor-pointer"
                  />
                  <label htmlFor="click-popup" className="text-gray-700 cursor-pointer">
                    Enable Click Popup
                  </label>
                </div>
              </div>
            </div>
          )}
        </div>

        <BaseMapSettings
          openBaseMapSet={openBaseMapSet}
          onClose={() => setOpenBaseMapSet(false)}
          setBaseMapUrl={setBaseMapUrl}
          setBaseMapAttribution={setBaseMapAttribution}
        />

        {/* FILE MENU */}
        <div className="relative" ref={fileRef}>
          <button
            onClick={() => {
              setOpenFileMenu(!openFileMenu);
              setOpenBasemapMenu(false);
              setOpenSettings(false);
            }}
            onMouseDown={(e) => e.stopPropagation()}
            className={BUTTON_STYLE}
            disabled={exporting || exportingLayers || importing}
            aria-label="File menu"
          >
            File
          </button>

          {openFileMenu && (
            <div className="absolute top-full left-0 mt-2 bg-white rounded-lg shadow-xl p-2 z-50 min-w-[220px]">
              <button
                onClick={handleImportScriptsClick}
                disabled={exporting || exportingLayers || importing}
                className="w-full text-left px-3 py-2 rounded-md text-gray-800 hover:bg-gray-100 disabled:opacity-60"
              >
                {importing ? "Importing..." : "Import scripts"}
              </button>
              <button
                onClick={handleExportScripts}
                disabled={exporting || exportingLayers || importing}
                className="w-full text-left px-3 py-2 rounded-md text-gray-800 hover:bg-gray-100 disabled:opacity-60"
              >
                {exporting ? "Exporting..." : "Export scripts"}
              </button>
              <button
                onClick={handleExportLayers}
                disabled={exporting || exportingLayers || importing}
                className="w-full text-left px-3 py-2 rounded-md text-gray-800 hover:bg-gray-100 disabled:opacity-60"
              >
                {exportingLayers ? "Exporting..." : "Export layers"}
              </button>
            </div>
          )}
          
          {/* Hidden file input for importing scripts */}
          <input
            ref={importFileInputRef}
            type="file"
            accept=".zip"
            onChange={handleImportScriptsFile}
            style={{ display: 'none' }}
            aria-hidden="true"
          />
        </div>
      </div>


      <img src={logo} alt="Logo" className="h-10 w-20 object-contain transform scale-250 mr-10" />

      {/* EXPORT ERROR MODAL */}
      <WindowTemplate
        isOpen={exportErrorOpen}
        title="Export all scripts"
        onClose={() => setExportErrorOpen(false)}
        widthClassName="w-[520px] max-w-[95%]"
        disableOverlayClose={false}
      >
        <div className="space-y-3">
          <p style={{ color: "#b91c1c", fontWeight: 600 }}>Não foi possível guardar o ficheiro.</p>
          <p style={{ color: "#111827" }}>{exportErrorMsg}</p>

          <div className="flex justify-end pt-2">
            <button
              onClick={() => setExportErrorOpen(false)}
              className="rounded-lg bg-[#0D73A5] text-white hover:bg-[#39AC73] px-4 py-2"
            >
              OK
            </button>
          </div>
        </div>
      </WindowTemplate>

      {/* EXPORT LAYERS ERROR MODAL */}
      <WindowTemplate
        isOpen={exportLayersErrorOpen}
        title="Export all layers"
        onClose={() => setExportLayersErrorOpen(false)}
        widthClassName="w-[520px] max-w-[95%]"
        disableOverlayClose={false}
      >
        <div className="space-y-3">
          <p style={{ color: "#b91c1c", fontWeight: 600 }}>Não foi possível guardar o ficheiro.</p>
          <p style={{ color: "#111827" }}>{exportLayersErrorMsg}</p>

          <div className="flex justify-end pt-2">
            <button
              onClick={() => setExportLayersErrorOpen(false)}
              className="rounded-lg bg-[#0D73A5] text-white hover:bg-[#39AC73] px-4 py-2"
            >
              OK
            </button>
          </div>
        </div>
      </WindowTemplate>

      {/* IMPORT SCRIPTS ERROR MODAL */}
      <WindowTemplate
        isOpen={importErrorOpen}
        title="Import scripts"
        onClose={() => setImportErrorOpen(false)}
        widthClassName="w-[520px] max-w-[95%]"
        disableOverlayClose={false}
      >
        <div className="space-y-3">
          <p style={{ color: "#b91c1c", fontWeight: 600 }}>Failed to import scripts.</p>
          <p style={{ color: "#111827" }}>{importErrorMsg}</p>

          <div className="flex justify-end pt-2">
            <button
              onClick={() => setImportErrorOpen(false)}
              className="rounded-lg bg-[#0D73A5] text-white hover:bg-[#39AC73] px-4 py-2"
            >
              OK
            </button>
          </div>
        </div>
      </WindowTemplate>
    </div>
  );
}

export default Header;
