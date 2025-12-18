import {useState, useRef, useEffect} from "react";
import BaseMapSettings from "./BaseMapSettings";

function EditMenu({ open, setBaseMapUrl, setBaseMapAttribution, setOpen }: { open: boolean; setBaseMapUrl: (url: string) => void; setBaseMapAttribution: (attribution: string) => void; setOpen: (open: boolean) => void }) {
  const [openBaseMapSet, setOpenBaseMapSet] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      // Prevent closing the menu if the BaseMapSettings window is open
      if (openBaseMapSet) {
        return;
      }

      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, [setOpen, openBaseMapSet]); // add openBaseMapSet to the dependency list

  if (!open){
    return null;
  }

  return (
    <div
      className="absolute top-full left-0 mt-2 bg-white border border-gray-200 rounded-lg shadow-lg w-40 z-9999"
      ref={menuRef}
    >
      <button onClick={()=>setOpenBaseMapSet(!openBaseMapSet)}className="w-full text-black text-left px-4 py-2 hover:bg-gray-100">
        Edit Base Map
      </button>
      <button className="w-full text-black text-left px-4 py-2 hover:bg-gray-100">
        Settings
      </button>
      <BaseMapSettings openBaseMapSet={openBaseMapSet} onClose={() => setOpenBaseMapSet(false)} setBaseMapUrl={setBaseMapUrl} setBaseMapAttribution={setBaseMapAttribution}/>
    </div>

  );
}

export default EditMenu;
