import type { RotationPlan } from "@/types/api";

export function rotationKey(rotation: RotationPlan): string {
  return [rotation.Y1_kharif, rotation.Y1_rabi, rotation.Y2_kharif, rotation.Y2_rabi].map((c) => c ?? "_").join("|");
}
