"use client";

import { Languages } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useI18n } from "@/i18n";

export function LanguageToggle() {
  const { locale, toggleLocale, t } = useI18n();

  return (
    <Button variant="ghost" size="sm" aria-label={t("language.toggle")} onClick={toggleLocale} className="gap-1.5">
      <Languages className="h-4 w-4" />
      {locale === "en" ? "اردو" : "English"}
    </Button>
  );
}
