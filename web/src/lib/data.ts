import type { Cell, ModelId, Replay } from "../types";
import { addDays, daysBetween, doy365 } from "./time";

declare const __INLINE_DATA__: boolean;

export async function loadReplay(): Promise<Replay> {
  if (__INLINE_DATA__) {
    const mod = await import("../../public/data/replay.json");
    return mod.default as unknown as Replay;
  }
  const res = await fetch("./data/replay.json", { cache: "no-cache" });
  if (!res.ok) throw new Error(`replay.json: HTTP ${res.status}`);
  return res.json();
}

export class View {
  constructor(public d: Replay) {}

  obs(date: string): number | null {
    const i = daysBetween(this.d.obs.start, date);
    return i >= 0 && i < this.d.obs.values.length ? this.d.obs.values[i] : null;
  }

  p90(date: string): number | null {
    return this.d.clim.p90[doy365(date) - 1];
  }

  climMean(date: string): number | null {
    return this.d.clim.mean[doy365(date) - 1];
  }

  /** newest eligible observation date */
  get lastObsDate(): string {
    const v = this.d.obs.values;
    for (let i = v.length - 1; i >= 0; i--) if (v[i] != null) return addDays(this.d.obs.start, i);
    return this.d.obs.start;
  }

  cell(model: ModelId, originIdx: number, lead: number): Cell {
    return this.d.forecasts[model]?.[originIdx]?.[lead - 1] ?? null;
  }

  alertFor(origin: string) {
    return this.d.alerts.find((a) => a.origin_date === origin) ?? null;
  }

  lastObsFor(originIdx: number): string {
    return addDays(this.d.origins[originIdx], -1);
  }
}

export const MODEL_LABEL: Record<ModelId, string> = {
  weather_corr_v1: "StreamPulse (water + ECMWF air)",
  water_ridge_v1: "Water-history only",
  persistence: "Persistence (yesterday stays)",
  climatology: "Climatology (2010–2023)",
};

export const MODEL_SHORT: Record<ModelId, string> = {
  weather_corr_v1: "StreamPulse",
  water_ridge_v1: "Water-only",
  persistence: "Persistence",
  climatology: "Climatology",
};

export const fmtC = (x: number | null | undefined, digits = 1) =>
  x == null || !Number.isFinite(x) ? "–" : `${x.toFixed(digits)} °C`;

export const pct = (x: number | null | undefined, digits = 0) =>
  x == null || !Number.isFinite(x) ? "–" : `${(x * 100).toFixed(digits)}%`;
