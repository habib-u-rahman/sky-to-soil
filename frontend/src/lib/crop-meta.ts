/** Visual metadata (icon, color) for each crop id in the knowledge base.
 * Purely presentational — not part of the API contract. */

export interface CropVisual {
  icon: string;
  color: string;
}

export const CROP_VISUALS: Record<string, CropVisual> = {
  wheat: { icon: "🌾", color: "var(--chart-4)" },
  rice: { icon: "🌱", color: "var(--sky)" },
  maize: { icon: "🌽", color: "var(--chart-4)" },
  cotton: { icon: "☁️", color: "var(--muted-foreground)" },
  sugarcane: { icon: "🎋", color: "var(--crop)" },
  chickpea: { icon: "🫘", color: "var(--soil)" },
  lentil: { icon: "🟤", color: "var(--soil)" },
  mungbean: { icon: "🟢", color: "var(--crop)" },
  sorghum: { icon: "🌿", color: "var(--chart-4)" },
  pearl_millet: { icon: "🌿", color: "var(--chart-4)" },
  mustard: { icon: "🌼", color: "var(--warning)" },
  potato: { icon: "🥔", color: "var(--soil)" },
  berseem_clover: { icon: "☘️", color: "var(--crop)" },
  soybean: { icon: "🫛", color: "var(--crop)" },
};

export const FALLOW_VISUAL: CropVisual = { icon: "—", color: "var(--muted)" };

export function cropVisual(cropId: string | null): CropVisual {
  if (!cropId) return FALLOW_VISUAL;
  return CROP_VISUALS[cropId] ?? { icon: "🌾", color: "var(--muted-foreground)" };
}

export function cropLabel(cropId: string | null, crops: { id: string; name: string }[]): string {
  if (!cropId) return "—";
  return crops.find((c) => c.id === cropId)?.name ?? cropId;
}
