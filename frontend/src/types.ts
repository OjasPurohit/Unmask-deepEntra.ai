// THE contract. Mirror of backend/schemas.py — change both together. OWNER: Ojas.
export type Band = "clean" | "inconclusive" | "strong";
export interface Signal { id: "classifier"|"ela"|"fft"|"noise"|"metadata"; name: string; score: number; weight: number;
  contribution: number; reason: string; heatmap?: string; panel?: string; details?: Record<string, unknown>; ok: boolean; error?: string }
// S1 `classifier` carries two sub-scores in details: { cf: number, probe: number }; score = max(cf, probe).
// Fusion contributions are keyed by feature, so "cf" and "probe" appear separately in ContributionBars.
export interface RegionScore { region: "left_eye"|"right_eye"|"mouth"|"nose"|"jaw_boundary"|"skin"|"background"; suspicion: number }
export interface Review { decision: "agree"|"disagree"|"needs_more"; note: string; at: string }
export interface AnalysisResult {
  case_id: string; sha256: string; filename: string; media_type: "image"; created_at: string;
  original: string;            // url of the uploaded image
  overlay: string;             // url of heatmap overlay, same size as original
  fused_score: number; band: Band; headline: string;   // e.g. "Suspicion concentrated at jaw boundary"
  signals: Signal[]; regions: RegionScore[];
  robustness: { jpeg50: number; resize50: number };
  explanation: string; limitations: string[]; disclaimer: string;
  timings_ms: Record<string, number>; review?: Review;
}
export interface CaseSummary { case_id: string; filename: string; media_type: string; fused_score: number; band: Band; created_at: string; review?: Review }
export interface Sample { name: string; url: string; kind: "image"; label_hint: string }
export interface Health { models_loaded: boolean; device: string }
