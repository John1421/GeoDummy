import { useEffect } from "react";

interface Basemap {
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

          const defaultBasemap = basemaps[0];

          setBaseMapUrl(defaultBasemap.url);
          setBaseMapAttribution(defaultBasemap.attribution ?? "");
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
