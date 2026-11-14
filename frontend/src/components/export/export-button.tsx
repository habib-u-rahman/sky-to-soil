"use client";

import { Download, Loader2 } from "lucide-react";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { useI18n } from "@/i18n";
import { generateFarmPlanPdf } from "@/lib/pdf-export";
import type { FarmAnalyzeResponse } from "@/types/api";

export function ExportButton({ data }: { data: FarmAnalyzeResponse }) {
  const { t } = useI18n();
  const [generating, setGenerating] = useState(false);

  async function handleClick() {
    setGenerating(true);
    try {
      await new Promise((resolve) => setTimeout(resolve, 150));
      generateFarmPlanPdf(data);
    } finally {
      setGenerating(false);
    }
  }

  return (
    <Button variant="outline" size="sm" onClick={handleClick} disabled={generating} className="gap-1.5">
      {generating ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Download className="h-3.5 w-3.5" />}
      {generating ? t("export.generating") : t("export.downloadPlan")}
    </Button>
  );
}
