import {useState} from "react";
import EditMenu from "./EditMenu";
const BUTTON_STYLE = " text-white font-[inter] font-semibold py-2 px-4 rounded-lg hover:bg-[#39AC73] transition justify-between";
function Header() {
  const [open, setOpen] = useState(false);

  return (
    <div className="w-full bg-linear-to-r from-[#0D73A5] to-[#99E0B9] text-white px-4 py-2 flex items-center justify-between">
      
      <div className="relative">  
        <button 
          onClick={() => setOpen(!open)} 
          className={BUTTON_STYLE}
        >
          Edit
        </button>

        <EditMenu open={open} />
      </div>

      <img
        src="src/assets/logo.png"
        alt="Logo"
        className="h-10 w-20 object-contain transform scale-250 mr-10"
      />
    </div>
  );
}


export default Header;