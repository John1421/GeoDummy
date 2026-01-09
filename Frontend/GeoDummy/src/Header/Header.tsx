import { useState, useEffect, useRef } from "react";
import BaseMapSettings from "./BaseMapSettings";
import logo from "../assets/logo.png";

const BUTTON_STYLE = "text-white font-semibold py-2 px-4 hover:opacity-80 transition";

type HeaderProps = {
  setBaseMapUrl: (url: string) => void;
  setBaseMapAttribution: (attribution: string) => void;
  enableHoverHighlight: boolean;
  setEnableHoverHighlight: (enabled: boolean) => void;
  enableClickPopup: boolean;
  setEnableClickPopup: (enabled: boolean) => void;
};

function Header({ 
  setBaseMapUrl, 
  setBaseMapAttribution,
  enableHoverHighlight,
  setEnableHoverHighlight,
  enableClickPopup,
  setEnableClickPopup
}: HeaderProps) {
  const [openBaseMapSet, setOpenBaseMapSet] = useState(false);
  const [openSettings, setOpenSettings] = useState(false);
  const settingsRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (settingsRef.current && !settingsRef.current.contains(event.target as Node)) {
        setOpenSettings(false);
      }
    };

    if (openSettings) {
      document.addEventListener('mousedown', handleClickOutside);
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [openSettings]);

  return (
    <div className="w-full bg-linear-to-r from-[#0D73A5] to-[#99E0B9] text-white px-4 py-2 flex items-center justify-between">

      <div className="flex gap-4 relative">
        <div className="relative" ref={settingsRef}>
          <button
            data-testid="settings-button"
            onClick={() => setOpenSettings(!openSettings)}
            onMouseDown={(e) => e.stopPropagation()}
            className={BUTTON_STYLE}
          >
            Settings
          </button>

          {openSettings && (
            <div className="absolute top-full left-0 mt-2 bg-white rounded-lg shadow-xl p-4 z-50 min-w-[250px]">
              <div className="space-y-3">
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

        <button
          data-testid="edit-basemap-button"
          onClick={() => setOpenBaseMapSet(!openBaseMapSet)}
          onMouseDown={(e) => e.stopPropagation()}
          className={BUTTON_STYLE}
        >
          Basemap
        </button>

        <BaseMapSettings 
          openBaseMapSet={openBaseMapSet} 
          onClose={() => setOpenBaseMapSet(false)} 
          setBaseMapUrl={setBaseMapUrl} 
          setBaseMapAttribution={setBaseMapAttribution} 
        />
      </div>

      <img
        src={logo}
        alt="Logo"
        className="h-10 w-20 object-contain transform scale-250 mr-10"
      />
    </div>
  );
}


export default Header;