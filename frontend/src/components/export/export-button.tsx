"use client";

import { Download, Loader2 } from "lucide-react";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { useI18n } from "@/i18n";
import { api, ApiError } from "@/lib/api-client";
import type { FarmAnalyzeResponse } from "@/types/api";

interface ExportButtonProps {
  data: FarmAnalyzeResponse;
  currentCrops: string[];
  isDemo: boolean;
}

export function ExportButton({ data, currentCrops, isDemo }: ExportButtonProps) {
  const { t } = useI18n();
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleClick() {
    setGenerating(true);
    setError(null);
    try {
      // The backend's PDF narrative is always generated in English (it
      // hardcodes "en" for the advisor call that writes it), so there's no
      // Urdu variant to request here.
      const blob = await api.reportPdf({ analysis: data, current_crops: currentCrops, language: "en", top_n: 3 }, isDemo);
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `sky-to-soil-farm-plan-${data.location.lat.toFixed(2)}-${data.location.lon.toFixed(2)}.pdf`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      // Revoking immediately races the browser's download handoff in some
      // builds (observed: download reaches 100% received, then its state
      // flips to "canceled") -- give it a moment to actually hand the blob
      // to the download manager before freeing it.
      setTimeout(() => URL.revokeObjectURL(url), 2000);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Couldn't generate the PDF.");
    } finally {
      setGenerating(false);
    }
  }

  return (
    <div className="flex items-center gap-2">
      <Button variant="outline" size="sm" onClick={handleClick} disabled={generating} className="gap-1.5">
        {generating ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Download className="h-3.5 w-3.5" />}
        {generating ? t("export.generating") : t("export.downloadPlan")}
      </Button>
      {error && <span className="text-xs text-destructive">{error}</span>}
    </div>
  );
}
