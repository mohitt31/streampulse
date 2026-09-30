/**
 * Dissolved-oxygen solubility in fresh water at 1 atm (mg/L), Benson & Krause (1984),
 * as given in APHA Standard Methods 4500-O. Physics, not a fitted model: it is the most
 * oxygen water at this temperature can hold when fully saturated.
 */
export function doSaturation(tempC: number): number {
  const T = tempC + 273.15;
  return Math.exp(-139.34411 + 1.575701e5 / T - 6.642308e7 / T ** 2 + 1.2438e10 / T ** 3 - 8.621949e11 / T ** 4);
}
