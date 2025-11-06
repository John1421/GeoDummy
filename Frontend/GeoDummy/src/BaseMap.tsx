import { useEffect } from "react";
//Coimbra coordinates
const INITIAL_LATITUDE = 40.2033;
const INITIAL_LONGITUDE = -8.4103;
const INITIAL_ZOOM = 10;
const BASE_MAPS:{ [key: string]: string } ={
  "OpenStreetMap":"https://tile.openstreetmap.org/{z}/{x}/{y}.png"
}
function BaseMap() {
  useEffect(() => {
    const map = L.map("map").setView([INITIAL_LATITUDE, INITIAL_LONGITUDE], INITIAL_ZOOM);
    L.tileLayer(BASE_MAPS["OpenStreetMap"], {
      maxZoom: 20,
      attribution:
        '&copy; <a href="http://www.openstreetmap.org/copyright">OpenStreetMap</a>',
    }).addTo(map);
    return () => map.remove();
  }, []);

  return (
    <div className="flex items-center justify-center min-h-screen">
      <div id="map" className="h-[600px] w-[1000px] rounded-sm translate-y-[5px]" />
    </div>
  );

}

export default BaseMap;