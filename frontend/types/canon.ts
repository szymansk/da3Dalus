/** An aircraft of the kernel's reference fleet (GET /canon/fleet). */
export interface CanonFleetEntry {
  id: string;
  name: string;
  mass_kg: number;
  /** Flap deflections in degrees by canon input slug; empty for an aircraft without flaps. */
  flap_deflections: Record<string, number>;
}
