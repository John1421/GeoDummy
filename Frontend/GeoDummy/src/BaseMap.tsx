import { useEffect } from "react";
//Portugal center coordinates
const INITIAL_LATITUDE = 39.557191;
const INITIAL_LONGITUDE = -7.8536599;
const INITIAL_ZOOM = 7;
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
    <div className="flex items-start justify-center ">
      <div id="map" className="h-[590px] w-[1000px] rounded-sm " />
    </div>
  );

}

export default BaseMap;