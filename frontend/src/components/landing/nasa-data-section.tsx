"use client";

import { CloudSun, Satellite, Sprout } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useI18n } from "@/i18n";

export function NasaDataSection() {
  const { t } = useI18n();

  const sources = [
    { icon: CloudSun, name: t("landing.nasaPower"), desc: t("landing.nasaPowerDesc"), accent: "text-sky" },
    { icon: Satellite, name: t("landing.modisNdvi"), desc: t("landing.modisNdviDesc"), accent: "text-crop" },
    { icon: Sprout, name: t("landing.soilGrids"), desc: t("landing.soilGridsDesc"), accent: "text-soil" },
  ];

  return (
    <section className="bg-muted/30 py-16">
      <div className="mx-auto max-w-6xl px-4 sm:px-6 lg:px-8">
        <div className="mx-auto max-w-2xl text-center">
          <h2 className="text-3xl font-bold text-foreground">{t("landing.nasaDataTitle")}</h2>
          <p className="mt-3 text-muted-foreground">{t("landing.nasaDataSubtitle")}</p>
        </div>

        <div className="mt-10 grid grid-cols-1 gap-4 sm:grid-cols-3">
          {sources.map((source) => (
            <Card key={source.name}>
              <CardHeader>
                <source.icon className={`h-6 w-6 ${source.accent}`} />
                <CardTitle className="mt-2 text-base">{source.name}</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-muted-foreground">{source.desc}</p>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    </section>
  );
}
