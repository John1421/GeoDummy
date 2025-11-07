const BUTTON_STYLE = " text-white font-[inter] font-semibold py-2 px-4 rounded-lg hover:bg-[#0B5E87] transition justify-between";
function Header() {
    const openFile=()=>{
        console.log("Open file");
    }
    const openEditMenu=()=>{
        console.log("Edit");
    }
    const openSettingsMenu=()=>{
        console.log("Settings");
    }
    return (
        <div className="w-full bg-linear-to-r from-[#0D73A5] to-[#99E0B9] text-white px-4 py-2 flex items-center justify-between">
            {/* All buttons + image in same div */}
            <div>
                <button onClick={openFile} className={BUTTON_STYLE}>File</button>
                <button onClick={openEditMenu} className={BUTTON_STYLE}>Edit</button>
                <button onClick={openSettingsMenu} className={BUTTON_STYLE}>Settings</button>
            </div>

            <img
                src="src/assets/logo.png"
                alt="Logo"
                className="h-10 w-20 object-contain transform scale-250 mr-10"
            />
        </div>
    )
}

export default Header;