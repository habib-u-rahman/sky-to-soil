"use client";

import { Check } from "lucide-react";
import { cn } from "@/lib/utils";

interface StepperProps {
  steps: string[];
  currentStep: number;
}

export function Stepper({ steps, currentStep }: StepperProps) {
  return (
    <ol className="flex items-center gap-1 sm:gap-2">
      {steps.map((label, i) => {
        const stepNumber = i + 1;
        const state = stepNumber < currentStep ? "done" : stepNumber === currentStep ? "active" : "upcoming";
        return (
          <li key={label} className="flex flex-1 items-center gap-1 sm:gap-2">
            <div className="flex items-center gap-2">
              <span
                className={cn(
                  "flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-xs font-semibold transition-colors",
                  state === "done" && "bg-primary text-primary-foreground",
                  state === "active" && "bg-primary text-primary-foreground ring-4 ring-primary/20",
                  state === "upcoming" && "bg-muted text-muted-foreground"
                )}
              >
                {state === "done" ? <Check className="h-3.5 w-3.5" /> : stepNumber}
              </span>
              <span
                className={cn(
                  "hidden text-sm font-medium sm:inline",
                  state === "upcoming" ? "text-muted-foreground" : "text-foreground"
                )}
              >
                {label}
              </span>
            </div>
            {stepNumber < steps.length && (
              <span className={cn("h-px flex-1", state === "done" ? "bg-primary" : "bg-border")} />
            )}
          </li>
        );
      })}
    </ol>
  );
}
