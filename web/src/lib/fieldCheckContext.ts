import type { Alert } from '../types';
import type { Resource, ForecastObservation, FieldCheckSite } from './fhirFieldCheck';
interface Catalog {
  location: Resource; resources: Record<string, Resource>;
  alerts: Record<string, { forecasts: string[]; closure: string[] }>;
}
declare const __INLINE_DATA__: boolean;
let pending: Promise<Catalog> | undefined;
export async function loadFieldCheckContext(alert: Alert): Promise<{ forecasts: ForecastObservation[]; site: FieldCheckSite }> {
  pending ??= (__INLINE_DATA__
    ? import('../../public/data/field-checks.json').then(module => module.default as unknown as Catalog)
    : fetch(`${import.meta.env.BASE_URL}data/field-checks.json`)
      .then(response => { if (!response.ok) throw new Error('Could not load the frozen FHIR context. Try again when the site is reachable.'); return response.json() as Promise<Catalog>; }))
    .catch(error => { pending = undefined; throw error; });
  const catalog = await pending;
  const entry = catalog.alerts[alert.alert_id];
  if (!entry) throw new Error('No frozen FHIR evidence is available for this alert.');
  return {
    forecasts: entry.forecasts.map(id => catalog.resources[id] as ForecastObservation),
    site: { location: catalog.location, supportingResources: entry.closure.filter(id => !entry.forecasts.includes(id)).map(id => catalog.resources[id]) },
  };
}
