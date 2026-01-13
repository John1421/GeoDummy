import { useEffect } from "react";

interface Basemap {
  id: string;
  url: string;
  attribution?: string;
}

export function useInitializeBasemap(
  setBaseMapUrl: (url: string) => void,
  setBaseMapAttribution: (attr: string) => void
) {
  useEffect(() => {
    const maxRetries = 3;
    const retryDelay = 1000;

    async function initBasemap() {
      for (let attempt = 1; attempt <= maxRetries; attempt++) {
        try {
          const response = await fetch("http://localhost:5050/basemaps");

          if (!response.ok) {
            throw new Error("Error retrieving basemaps");
          }

          const basemaps: Basemap[] = await response.json();

          if (!basemaps.length) {
            throw new Error("Empty basemap list");
          }

          // Check for saved basemap in localStorage
          const savedBasemapId = localStorage.getItem('selectedBasemapId');
          let selectedBasemap = basemaps[0];
          
          if (savedBasemapId) {
            const savedBasemap = basemaps.find((b: Basemap & { id: string }) => b.id === savedBasemapId);
            if (savedBasemap) {
              selectedBasemap = savedBasemap;
            }
          }

          setBaseMapUrl(selectedBasemap.url);
          setBaseMapAttribution(selectedBasemap.attribution ?? "");
          return;
        } catch (err) {
          if (attempt === maxRetries) {
            console.error("Failed to initialize default basemap", err);
          } else {
            await new Promise((r) => setTimeout(r, retryDelay));
          }
        }
      }
    }

    initBasemap();
  }, [setBaseMapUrl, setBaseMapAttribution]);
}
