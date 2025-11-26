import { useState } from "react";

const BASEMAPS = [
    { id: "OSM Standard", url: "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" },
    { id: "ESRI Satellite", url: "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}" },
    { id: "OpenTopoMap", url: "https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png" },
    { id: "Carto Light", url: "https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png" },
    { id: "Carto Dark", url: "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png" }
];
function BaseMapSettings({
    openBaseMapSet,
    onClose,
    setBaseMapUrl,
}: {
    openBaseMapSet: boolean;
    onClose: () => void;
    setBaseMapUrl: (url: string) => void;
}) {
    const [selectedBasemap, setSelectedBasemap] = useState(BASEMAPS[0].url);

    function handleChange(event: React.ChangeEvent<HTMLSelectElement>) {
        setSelectedBasemap(event.target.value);
    }

    async function save_basemap() {
        setBaseMapUrl(selectedBasemap);
        onClose();

    }

    if (!openBaseMapSet) return null;


    return (
        <div className="fixed inset-0 flex items-center justify-center bg-black/20 z-9999">
            <div className="bg-white border border-gray-200 rounded-lg shadow-lg w-1/3 h-1/5 p-4">


                <label htmlFor="basemap" className="text-black font-bold">
                    Choose BaseMap
                </label>

                <select
                    id="basemap"
                    onChange={handleChange}
                    value={selectedBasemap} // make it controlled
                    className="text-black w-full mt-2 bg-[#DADFE7] rounded-lg py-1"
                    name="basemap"
                >
                    {BASEMAPS.map((map) => (
                        <option key={map.id} value={map.url}>
                            {map.id}
                        </option>
                    ))}
                </select>

                <button
                    onClick={save_basemap}
                    className="ml-auto mt-5 block rounded-lg bg-[#0D73A5] text-white hover:bg-[#39AC73] w-1/5 py-1 "
                >
                    Save
                </button>


            </div>
        </div>
    );
}

export default BaseMapSettings;
