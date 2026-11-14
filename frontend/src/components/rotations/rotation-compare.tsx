"use client";

import { RotationTimeline } from "@/components/rotations/rotation-timeline";
import { SubScoreBars } from "@/components/rotations/sub-score-radar";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { useI18n } from "@/i18n";
import type { CropProfile, ScoredRotation } from "@/types/api";

interface RotationCompareProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  rotations: ScoredRotation[];
  crops: CropProfile[] | null;
}

export function RotationCompare({ open, onOpenChange, rotations, crops }: RotationCompareProps) {
  const { t } = useI18n();

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>{t("rotations.compareTitle")}</DialogTitle>
        </DialogHeader>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          {rotations.map((rotation, i) => (
            <div key={i} className="space-y-3 rounded-lg border border-border p-3">
              <div className="flex items-center justify-between">
                <span className="text-sm font-semibold text-foreground">{t("rotations.scoreLabel")}</span>
                <span className="text-lg font-bold text-primary">{Math.round(rotation.priority_weighted_score_0_100)}</span>
              </div>
              <RotationTimeline rotation={rotation.rotation} crops={crops} />
              <SubScoreBars subScores={rotation.sub_scores} />
              {rotation.reasons.length > 0 && (
                <ul className="space-y-1 text-xs text-foreground">
                  {rotation.reasons.map((reason) => (
                    <li key={reason} className="flex gap-1.5">
                      <span className="text-success">+</span>
                      {reason}
                    </li>
                  ))}
                </ul>
              )}
            </div>
          ))}
        </div>
      </DialogContent>
    </Dialog>
  );
}
