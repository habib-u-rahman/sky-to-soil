export interface GeocodeResult {
  label: string;
  lat: number;
  lon: number;
}

/** Free-tier OpenStreetMap Nominatim search — no API key required.
 * Rate-limited and best-effort; fine for an occasional location search. */
export async function searchPlaces(query: string): Promise<GeocodeResult[]> {
  if (!query.trim()) return [];
  const url = new URL("https://nominatim.openstreetmap.org/search");
  url.searchParams.set("q", query);
  url.searchParams.set("format", "jsonv2");
  url.searchParams.set("limit", "6");

  const res = await fetch(url.toString(), {
    headers: { Accept: "application/json" },
  });
  if (!res.ok) return [];

  const data: Array<{ display_name: string; lat: string; lon: string }> = await res.json();
  return data.map((item) => ({
    label: item.display_name,
    lat: Number.parseFloat(item.lat),
    lon: Number.parseFloat(item.lon),
  }));
}
