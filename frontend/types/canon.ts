/** An aircraft of the kernel's reference fleet (GET /canon/aircraft, group `fleet`). */
export interface CanonFleetEntry {
  id: string;
  name: string;
  mass_kg: number;
  /** Flap deflections in degrees by canon input slug; empty for an aircraft without flaps. */
  flap_deflections: Record<string, number>;
}

/** A stored aeroplane in its current state, the head of its main branch (group `aeroplanes`). */
export interface CanonAeroplaneEntry {
  id: string;
  name: string;
  /** The `mass` design assumption with its active source, in kg; null when there is none. */
  mass_kg: number | null;
}

/** The aircraft the Expert View can load (GET /canon/aircraft). */
export interface CanonAircraftList {
  fleet: CanonFleetEntry[];
  aeroplanes: CanonAeroplaneEntry[];
}

/** The aircraft of a compute request: a fleet aircraft or a stored aeroplane. */
export type CanonAircraftRef = { fleet: string } | { aeroplane: string };
