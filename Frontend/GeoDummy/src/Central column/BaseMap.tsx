import { useEffect, useRef, useState } from "react";
//Portugal center coordinates
const INITIAL_LATITUDE = 39.557191;
const INITIAL_LONGITUDE = -7.8536599;
const INITIAL_ZOOM = 7;

function BaseMap({ initialUrl }: { initialUrl: string }) {
  const [currentBaseMapUrl, setCurrentBaseMapUrl] = useState(initialUrl);
  const mapRef = useRef<L.Map | null>(null);
  const tileLayerRef = useRef<L.TileLayer | null>(null);

  // Initialize map once on component mount
  useEffect(() => {
    if (!mapRef.current) {
      mapRef.current = L.map("map").setView([INITIAL_LATITUDE, INITIAL_LONGITUDE], INITIAL_ZOOM);
    }

    return () => {
      if (mapRef.current) {
        mapRef.current.remove();
        mapRef.current = null;
      }
    };
  }, []);

  // Update tile layer when currentBaseMapUrl changes
  useEffect(() => {
    if (mapRef.current) {
      if (tileLayerRef.current) {
        mapRef.current.removeLayer(tileLayerRef.current);
      }

      tileLayerRef.current = L.tileLayer(currentBaseMapUrl, {
        maxZoom: 20,
        attribution:
          '&copy; <a href="http://www.openstreetmap.org/copyright">OpenStreetMap</a>',
      }).addTo(mapRef.current);
    }
  }, [currentBaseMapUrl]);

  // This function is for demonstration and to fulfill the previous task's export.
  // In a real application, you might use a context API or Redux for global state.
  useEffect(() => {
    setCurrentBaseMapUrl(initialUrl);
  }, [initialUrl]);

 return (
    <div className="flex-1 flex items-start justify-center w-full h-full ">
     
      <div id="map" className="h-full w-full" />
    </div>
  );
}

export default BaseMap;