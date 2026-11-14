"use client";

import { Bot, CheckCircle2, ShieldCheck } from "lucide-react";
import { RotationTimeline } from "@/components/rotations/rotation-timeline";
import { SubScoreBars } from "@/components/rotations/sub-score-radar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { useI18n } from "@/i18n";
import { cn } from "@/lib/utils";
import type { CropProfile, ScoredRotation, StressedRotationResult } from "@/types/api";

interface RotationCardProps {
  rotation: ScoredRotation;
  crops: CropProfile[] | null;
  stressResult?: StressedRotationResult;
  isSelected: boolean;
  onToggleSelect: () => void;
  compareDisabled: boolean;
  onViewDetails: () => void;
}

function scoreTone(score: number) {
  if (score >= 75) return "bg-success/15 text-success";
  if (score >= 55) return "bg-warning/15 text-warning";
  return "bg-destructive/15 text-destructive";
}

export function RotationCard({
  rotation,
  crops,
  stressResult,
  isSelected,
  onToggleSelect,
  compareDisabled,
  onViewDetails,
}: RotationCardProps) {
  const { t } = useI18n();
  const score = rotation.priority_weighted_score_0_100;

  return (
    <Card className={cn("relative transition-shadow", isSelected && "ring-2 ring-primary/50")}>
      <CardHeader className="gap-3">
        <div className="flex items-start justify-between gap-2">
          <div className={cn("flex h-12 w-12 flex-col items-center justify-center rounded-full text-sm font-bold", scoreTone(score))}>
            {Math.round(score)}
          </div>
          <div className="flex flex-col items-end gap-1.5">
            {stressResult && (
              <Tooltip>
                <TooltipTrigger
                  render={
                    <Badge variant="outline" className="gap-1 text-[10px]" />
                  }
                >
                  <ShieldCheck className="h-3 w-3 text-sky" />
                  {t("rotations.stressTestBadge")}
                </TooltipTrigger>
                <TooltipContent>
                  {t("rotations.resilienceLabel")}: {Math.round(stressResult.resilience_score_0_100)}/100 — {t("rotations.resilienceDesc")}
                </TooltipContent>
              </Tooltip>
            )}
            <Button
              size="sm"
              variant={isSelected ? "default" : "outline"}
              className="h-7 gap-1 text-xs"
              disabled={!isSelected && compareDisabled}
              onClick={onToggleSelect}
            >
              {isSelected && <CheckCircle2 className="h-3 w-3" />}
              {t("rotations.compareBtn")}
            </Button>
          </div>
        </div>

        <RotationTimeline rotation={rotation.rotation} crops={crops} />
      </CardHeader>

      <CardContent className="space-y-3">
        <SubScoreBars subScores={rotation.sub_scores} />

        {rotation.reasons.length > 0 && (
          <div>
            <p className="mb-1 text-[11px] font-semibold text-muted-foreground">{t("rotations.reasonsLabel")}</p>
            <ul className="space-y-1 text-xs text-foreground">
              {rotation.reasons.slice(0, 3).map((reason) => (
                <li key={reason} className="flex gap-1.5">
                  <span className="text-success">+</span>
                  <span>{reason}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {rotation.warnings.length > 0 && (
          <div>
            <p className="mb-1 text-[11px] font-semibold text-muted-foreground">{t("rotations.warningsLabel")}</p>
            <ul className="space-y-1 text-xs text-muted-foreground">
              {rotation.warnings.slice(0, 2).map((warning) => (
                <li key={warning} className="flex gap-1.5">
                  <span className="text-warning">!</span>
                  <span>{warning}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        <Button variant="ghost" size="sm" className="w-full gap-1.5 text-xs" onClick={onViewDetails}>
          <Bot className="h-3.5 w-3.5" />
          {t("rotations.viewDetails")}
        </Button>
      </CardContent>
    </Card>
  );
}
