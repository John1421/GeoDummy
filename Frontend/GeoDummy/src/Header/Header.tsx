import { useState } from "react";
import BaseMapSettings from "./BaseMapSettings";
import logo from "../assets/logo.png";

const BUTTON_STYLE = "text-white font-semibold py-2 px-4 hover:opacity-80 transition";

function Header({ setBaseMapUrl, setBaseMapAttribution }: { setBaseMapUrl: (url: string) => void; setBaseMapAttribution: (attribution: string) => void }) {
  const [openBaseMapSet, setOpenBaseMapSet] = useState(false);

  return (
    <div className="w-full bg-linear-to-r from-[#0D73A5] to-[#99E0B9] text-white px-4 py-2 flex items-center justify-between">

      <div className="flex gap-4">
        <button
          data-testid="settings-button"
          onClick={() => {}}
          onMouseDown={(e) => e.stopPropagation()}
          className={BUTTON_STYLE}
        >
          Settings
        </button>

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