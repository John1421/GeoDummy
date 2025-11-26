import {useState} from "react";
import BaseMapSettings from "./BaseMapSettings";

function EditMenu({ open, setBaseMapUrl }: { open: boolean; setBaseMapUrl: (url: string) => void }) {
  const [openBaseMapSet, setOpenBaseMapSet] = useState(false);
  if (!open){
    return null;
  }
  
  return (
    <div className="absolute top-full left-0 mt-2 bg-white border border-gray-200 rounded-lg shadow-lg w-40 z-9999">
      <button onClick={()=>setOpenBaseMapSet(!openBaseMapSet)}className="w-full text-black text-left px-4 py-2 hover:bg-gray-100">
        Edit Base Map
      </button>
      <button className="w-full text-black text-left px-4 py-2 hover:bg-gray-100">
        Settings
      </button>
      <BaseMapSettings openBaseMapSet={openBaseMapSet} onClose={() => setOpenBaseMapSet(false)} setBaseMapUrl={setBaseMapUrl}/>
    </div>

  );
}

export default EditMenu;
