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

  return (
    <div className="w-full bg-linear-to-r from-[#0D73A5] to-[#99E0B9] text-white px-4 py-2 flex items-center justify-between">
      <div className="flex gap-4 relative">
        {/* FILE MENU */}
        <div className="relative" ref={fileRef}>
          <button
            onClick={() => setOpenFileMenu(!openFileMenu)}
            onMouseDown={(e) => e.stopPropagation()}
            className={BUTTON_STYLE}
            disabled={exporting}
            aria-label="File menu"
          >
            File
          </button>

          {openFileMenu && (
            <div className="absolute top-full left-0 mt-2 bg-white rounded-lg shadow-xl p-2 z-50 min-w-[220px]">
              <button
                onClick={handleExportScripts}
                disabled={exporting}
                className="w-full text-left px-3 py-2 rounded-md text-gray-800 hover:bg-gray-100 disabled:opacity-60"
              >
                {exporting ? "Exporting..." : "Export scripts"}
              </button>
            </div>
          )}
        </div>

        {/* BASEMAP MENU */}
        <div className="relative" ref={basemapRef}>
          <button
            data-testid="edit-basemap-button"
            onClick={() => setOpenBasemapMenu(!openBasemapMenu)}
            onMouseDown={(e) => e.stopPropagation()}
            className={BUTTON_STYLE}
          >
            Basemap
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
      </div>

      <img src={logo} alt="Logo" className="h-10 w-20 object-contain transform scale-250 mr-10" />

      {/* EXPORT ERROR MODAL */}
      <WindowTemplate
        isOpen={exportErrorOpen}
        title="Export scripts"
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
    </div>
  );
}

export default Header;
