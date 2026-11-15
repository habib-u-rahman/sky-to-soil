"use client";

import "maplibre-gl/dist/maplibre-gl.css";
import { Map as MapLibreMap, Marker, NavigationControl, setWorkerUrl } from "maplibre-gl";
import { useEffect, useRef } from "react";
import type { Location } from "@/types/api";

// MapLibre auto-derives its worker script's URL from import.meta.url, and
// silently falls back to an empty string whenever that doesn't look like a
// real http(s) URL -- which it doesn't under Next.js/Turbopack's module
// wrapping, causing "Worker failed to load. Check that the worker URL is
// correct." with no map tiles ever rendering. public/maplibre-gl-worker.mjs
// is the exact matching worker bundle, copied out of node_modules on every
// `npm install` (see scripts/copy-maplibre-worker.js) and served as a plain
// static asset, so this URL always resolves correctly client-side.
if (typeof window !== "undefined") {
  setWorkerUrl("/maplibre-gl-worker.mjs");
}

interface MapPickerProps {
  value: Location | null;
  onChange: (location: Location) => void;
  className?: string;
}

/** MapLibre GL picker using the key-free MapLibre demo vector style, so the
 * demo works without any Mapbox/MapTiler API key. */
const DEMO_STYLE = "https://demotiles.maplibre.org/style.json";

export function MapPicker({ value, onChange, className }: MapPickerProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<MapLibreMap | null>(null);
  const markerRef = useRef<Marker | null>(null);
  const onChangeRef = useRef(onChange);

  useEffect(() => {
    onChangeRef.current = onChange;
  }, [onChange]);

  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;

    const startCenter: [number, number] = value ? [value.lon, value.lat] : [73.08, 31.42];
    const map = new MapLibreMap({
      container: containerRef.current,
      style: DEMO_STYLE,
      center: startCenter,
      zoom: value ? 8 : 4,
      attributionControl: { compact: true },
    });
    map.addControl(new NavigationControl({ showCompass: false }), "top-right");

    const marker = new Marker({ color: "var(--primary)", draggable: true })
      .setLngLat(startCenter)
      .addTo(map);

    marker.on("dragend", () => {
      const pos = marker.getLngLat();
      onChangeRef.current({ lat: Math.round(pos.lat * 10000) / 10000, lon: Math.round(pos.lng * 10000) / 10000 });
    });

    map.on("click", (e) => {
      marker.setLngLat(e.lngLat);
      onChangeRef.current({ lat: Math.round(e.lngLat.lat * 10000) / 10000, lon: Math.round(e.lngLat.lng * 10000) / 10000 });
    });

    mapRef.current = map;
    markerRef.current = marker;

    return () => {
      map.remove();
      mapRef.current = null;
      markerRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Sync external value changes (search result, geolocation) into the map.
  useEffect(() => {
    if (!value || !mapRef.current || !markerRef.current) return;
    const lngLat: [number, number] = [value.lon, value.lat];
    markerRef.current.setLngLat(lngLat);
    mapRef.current.flyTo({ center: lngLat, zoom: Math.max(mapRef.current.getZoom(), 8), duration: 800 });
  }, [value?.lat, value?.lon, value]);

  return <div ref={containerRef} className={className ?? "h-80 w-full rounded-lg"} />;
}
