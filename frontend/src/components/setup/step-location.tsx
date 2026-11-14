"use client";

import { Crosshair, MapPin, Search } from "lucide-react";
import { useState } from "react";
import { MapPicker } from "@/components/shared/map-picker";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { useI18n } from "@/i18n";
import { type GeocodeResult, searchPlaces } from "@/lib/geocode";
import type { Location } from "@/types/api";

interface StepLocationProps {
  location: Location | null;
  onChange: (location: Location, label?: string) => void;
}

export function StepLocation({ location, onChange }: StepLocationProps) {
  const { t } = useI18n();
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<GeocodeResult[]>([]);
  const [searching, setSearching] = useState(false);
  const [locating, setLocating] = useState(false);
  const [locationError, setLocationError] = useState<string | null>(null);

  async function handleSearch(e: React.FormEvent) {
    e.preventDefault();
    setSearching(true);
    try {
      const found = await searchPlaces(query);
      setResults(found);
    } finally {
      setSearching(false);
    }
  }

  function handleUseMyLocation() {
    if (!navigator.geolocation) return;
    setLocating(true);
    setLocationError(null);
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        onChange(
          { lat: Math.round(pos.coords.latitude * 10000) / 10000, lon: Math.round(pos.coords.longitude * 10000) / 10000 },
          undefined
        );
        setLocating(false);
      },
      () => {
        setLocationError(t("setup.locationDenied"));
        setLocating(false);
      },
      { timeout: 10000 }
    );
  }

  return (
    <div className="space-y-5">
      <div>
        <h2 className="text-xl font-semibold text-foreground">{t("setup.locationTitle")}</h2>
        <p className="mt-1 text-sm text-muted-foreground">{t("setup.locationDesc")}</p>
      </div>

      <div className="flex flex-col gap-2 sm:flex-row">
        <form onSubmit={handleSearch} className="flex flex-1 gap-2">
          <Input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder={t("setup.searchPlaceholder")}
            aria-label={t("common.search")}
          />
          <Button type="submit" variant="outline" disabled={searching}>
            <Search className="h-4 w-4" />
          </Button>
        </form>
        <Button variant="secondary" onClick={handleUseMyLocation} disabled={locating} className="gap-2">
          <Crosshair className="h-4 w-4" />
          {locating ? t("setup.locatingYou") : t("setup.useMyLocationBtn")}
        </Button>
      </div>

      {locationError && <p className="text-sm text-destructive">{locationError}</p>}

      {results.length > 0 && (
        <Card>
          <CardContent className="max-h-48 space-y-1 overflow-y-auto p-2">
            {results.length === 0 ? (
              <p className="px-2 py-1.5 text-sm text-muted-foreground">{t("setup.searchNoResults")}</p>
            ) : (
              results.map((result) => (
                <button
                  key={`${result.lat}-${result.lon}`}
                  type="button"
                  onClick={() => {
                    onChange({ lat: result.lat, lon: result.lon }, result.label);
                    setResults([]);
                    setQuery(result.label);
                  }}
                  className="flex w-full items-start gap-2 rounded-md px-2 py-1.5 text-start text-sm hover:bg-muted"
                >
                  <MapPin className="mt-0.5 h-3.5 w-3.5 shrink-0 text-muted-foreground" />
                  <span className="line-clamp-2">{result.label}</span>
                </button>
              ))
            )}
          </CardContent>
        </Card>
      )}

      <MapPicker value={location} onChange={(loc) => onChange(loc)} className="h-80 w-full rounded-lg border border-border" />

      {location && (
        <div className="flex flex-wrap items-center gap-4 rounded-lg border border-border bg-muted/40 px-4 py-3 text-sm">
          <span className="font-medium text-foreground">{t("setup.locationSelected")}</span>
          <span className="text-muted-foreground">
            {t("setup.latLabel")}: {location.lat.toFixed(4)}
          </span>
          <span className="text-muted-foreground">
            {t("setup.lonLabel")}: {location.lon.toFixed(4)}
          </span>
        </div>
      )}
    </div>
  );
}
