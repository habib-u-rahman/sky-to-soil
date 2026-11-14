"use client";

import { BadgeCheck, Bot, Send, Sparkles } from "lucide-react";
import { useState } from "react";
import { RotationTimeline } from "@/components/rotations/rotation-timeline";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { useI18n } from "@/i18n";
import type { CropProfile, ScoredRotation } from "@/types/api";

interface AgronomistPanelProps {
  rotation: ScoredRotation | null;
  crops: CropProfile[] | null;
}

export function AgronomistPanel({ rotation, crops }: AgronomistPanelProps) {
  const { t, locale } = useI18n();
  const [replyLang, setReplyLang] = useState<"en" | "ur">(locale);
  const [message, setMessage] = useState("");

  return (
    <div className="space-y-5">
      <div className="flex items-start gap-3">
        <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-primary/10 text-primary">
          <Bot className="h-4.5 w-4.5" />
        </span>
        <div>
          <h3 className="font-semibold text-foreground">{t("agronomist.title")}</h3>
          <p className="text-xs text-muted-foreground">{t("agronomist.subtitle")}</p>
        </div>
      </div>

      {rotation && (
        <div className="rounded-lg border border-border p-3">
          <RotationTimeline rotation={rotation.rotation} crops={crops} />
        </div>
      )}

      <div className="rounded-lg border border-dashed border-border bg-muted/30 p-4">
        <div className="mb-2 flex items-center gap-1.5 text-xs font-semibold text-muted-foreground">
          <Sparkles className="h-3.5 w-3.5" />
          {t("agronomist.placeholderExplanationTitle")}
        </div>
        <p className="text-sm leading-relaxed text-foreground">{t("agronomist.placeholderExplanationBody")}</p>

        {rotation && (
          <ul className="mt-3 space-y-1.5">
            {[...rotation.reasons, ...rotation.warnings].slice(0, 4).map((line) => (
              <li key={line} className="flex items-start gap-1.5 text-xs text-muted-foreground">
                <BadgeCheck className="mt-0.5 h-3.5 w-3.5 shrink-0 text-success" />
                <span>{line}</span>
              </li>
            ))}
          </ul>
        )}
      </div>

      <Badge variant="secondary" className="gap-1.5">
        <BadgeCheck className="h-3.5 w-3.5 text-success" />
        {t("agronomist.everyNumberVerified")}
      </Badge>

      <div className="space-y-2 border-t border-border pt-4">
        <div className="flex items-center justify-between">
          <span className="text-xs font-medium text-muted-foreground">{t("agronomist.languageLabel")}</span>
          <div className="flex gap-1">
            <Button
              size="sm"
              variant={replyLang === "en" ? "default" : "outline"}
              className="h-6 px-2 text-[11px]"
              onClick={() => setReplyLang("en")}
            >
              {t("language.english")}
            </Button>
            <Button
              size="sm"
              variant={replyLang === "ur" ? "default" : "outline"}
              className="h-6 px-2 text-[11px]"
              onClick={() => setReplyLang("ur")}
            >
              {t("language.urdu")}
            </Button>
          </div>
        </div>

        <Textarea
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          placeholder={t("agronomist.chatPlaceholder")}
          className="min-h-16 resize-none text-sm"
        />
        <div className="flex items-center justify-between">
          <p className="text-[11px] text-muted-foreground">{t("agronomist.comingSoonNotice")}</p>
          <Button size="sm" disabled className="gap-1.5">
            <Send className="h-3.5 w-3.5" />
            {t("agronomist.send")}
          </Button>
        </div>
      </div>

      <p className="text-[11px] text-muted-foreground">{t("agronomist.disclaimer")}</p>
    </div>
  );
}
