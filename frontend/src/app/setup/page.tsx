"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { StepCrops } from "@/components/setup/step-crops";
import { StepLocation } from "@/components/setup/step-location";
import { StepPriorities } from "@/components/setup/step-priorities";
import { StepSoil } from "@/components/setup/step-soil";
import { Stepper } from "@/components/setup/stepper";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { useI18n } from "@/i18n";
import { useFarmStore } from "@/lib/farm-store";
import { DEMO_LOCATION } from "@/lib/config";

export default function SetupPage() {
  const { t } = useI18n();
  const router = useRouter();
  const [step, setStep] = useState(1);

  const location = useFarmStore((s) => s.location);
  const soilOverride = useFarmStore((s) => s.soilOverride);
  const currentCrops = useFarmStore((s) => s.currentCrops);
  const priorities = useFarmStore((s) => s.priorities);
  const setLocation = useFarmStore((s) => s.setLocation);
  const setSoilOverride = useFarmStore((s) => s.setSoilOverride);
  const setCurrentCrops = useFarmStore((s) => s.setCurrentCrops);
  const setPriorities = useFarmStore((s) => s.setPriorities);
  const completeSetup = useFarmStore((s) => s.completeSetup);
  const loadDemoFarm = useFarmStore((s) => s.loadDemoFarm);

  const steps = [t("setup.stepLocation"), t("setup.stepSoil"), t("setup.stepCrops"), t("setup.stepPriorities")];
  const effectiveLocation = location ?? DEMO_LOCATION;

  function next() {
    if (step < 4) setStep(step + 1);
    else {
      completeSetup();
      router.push("/dashboard");
    }
  }

  function back() {
    if (step > 1) setStep(step - 1);
  }

  return (
    <div className="mx-auto max-w-3xl px-4 py-10 sm:px-6 lg:px-8">
      <div className="mb-8">
        <h1 className="font-heading text-3xl font-semibold tracking-tight text-foreground">{t("setup.title")}</h1>
        <button
          type="button"
          onClick={() => {
            loadDemoFarm();
            router.push("/dashboard");
          }}
          className="mt-1 text-sm text-primary underline-offset-4 hover:underline"
        >
          {t("setup.skipToDemo")}
        </button>
      </div>

      <div className="mb-8">
        <Stepper steps={steps} currentStep={step} />
      </div>

      <Card>
        <CardContent className="p-5 sm:p-6">
          {step === 1 && (
            <StepLocation
              location={location}
              onChange={(loc, label) => setLocation(loc, label)}
            />
          )}
          {step === 2 && <StepSoil location={effectiveLocation} override={soilOverride} onChange={setSoilOverride} />}
          {step === 3 && <StepCrops value={currentCrops} onChange={setCurrentCrops} />}
          {step === 4 && <StepPriorities value={priorities} onChange={setPriorities} />}
        </CardContent>
      </Card>

      <div className="mt-6 flex items-center justify-between">
        <Button variant="outline" onClick={back} disabled={step === 1}>
          {t("setup.backBtn")}
        </Button>
        <Button onClick={next} disabled={step === 1 && !location}>
          {step === 4 ? t("setup.finishBtn") : t("setup.nextBtn")}
        </Button>
      </div>
    </div>
  );
}
