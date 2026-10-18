import { useEffect, useRef, useState } from "react";
import "leaflet/dist/leaflet.css";
import type { MapSurfaceProps } from "./map-props";

// Native imports resolve MapSurface.native.tsx, not this browser implementation.
export default function MapSurface({ position }: MapSurfaceProps) {
  const element = useRef<HTMLDivElement>(null);
  const [failed, setFailed] = useState(false);
  useEffect(() => {
    let disposed = false;
    let cleanup = () => {};
    import("leaflet")
      .then((L) => {
        if (disposed || !element.current) return;
        const map = L.map(element.current).setView(
          [position.latitude, position.longitude],
          15,
        );
        L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
          maxZoom: 19,
          attribution: "&copy; OpenStreetMap contributors",
        })
          .addTo(map)
          .on("tileerror", () => setFailed(true));
        cleanup = () => map.remove();
      })
      .catch(() => setFailed(true));
    return () => {
      disposed = true;
      cleanup();
    };
  }, [position.latitude, position.longitude]);
  return (
    <div style={{ flex: 1, minHeight: 280, width: "100%" }}>
      <div
        ref={element}
        style={{ height: 350, width: "100%" }}
        aria-label="Street map"
      />
      {failed && (
        <p role="status">Street map unavailable. Check your connection.</p>
      )}
    </div>
  );
}
