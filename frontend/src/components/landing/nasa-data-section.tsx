"use client";

import { CloudSun, Satellite, Sprout } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useI18n } from "@/i18n";

export function NasaDataSection() {
  const { t } = useI18n();

  const sources = [
    {
      icon: CloudSun,
      name: t("landing.nasaPower"),
      desc: t("landing.nasaPowerDesc"),
      gradient: "from-sky to-sky/60",
    },
    {
      icon: Satellite,
      name: t("landing.modisNdvi"),
      desc: t("landing.modisNdviDesc"),
      gradient: "from-crop to-crop/60",
    },
    {
      icon: Sprout,
      name: t("landing.soilGrids"),
      desc: t("landing.soilGridsDesc"),
      gradient: "from-soil to-soil/60",
    },
  ];

  return (
    <section className="bg-muted/30 py-20">
      <div className="mx-auto max-w-6xl px-4 sm:px-6 lg:px-8">
        <div className="mx-auto max-w-2xl text-center">
          <h2 className="font-heading text-3xl font-semibold tracking-tight text-foreground sm:text-4xl">
            {t("landing.nasaDataTitle")}
          </h2>
          <p className="mt-3 text-muted-foreground">{t("landing.nasaDataSubtitle")}</p>
        </div>

        <div className="mt-10 grid grid-cols-1 gap-5 sm:grid-cols-3">
          {sources.map((source) => (
            <Card key={source.name} className="transition-all duration-200 hover:-translate-y-1 hover:shadow-lg">
              <CardHeader>
                <span
                  className={`flex h-11 w-11 items-center justify-center rounded-xl bg-gradient-to-br ${source.gradient} text-white shadow-sm`}
                >
                  <source.icon className="h-5 w-5" />
                </span>
                <CardTitle className="mt-3 text-base">{source.name}</CardTitle>
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
