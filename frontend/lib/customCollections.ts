// Client-side persistence for user-created documentation collections.
//
// Built-in collections (Python, FastAPI, …) are fixed in `collections.ts`. When a user
// uploads/ingests into a *new* collection name, we remember it here (localStorage) so it
// shows up in the Documentation list on future visits, with a green "has your docs" dot.

import { DOC_COLLECTIONS } from "./collections";
import type { DocCollection } from "./types";

const STORAGE_KEY = "rivr_custom_collections";

const BUILTIN_IDS = new Set(DOC_COLLECTIONS.map((c) => c.id.toLowerCase()));

export function isBuiltInCollection(id: string): boolean {
  return BUILTIN_IDS.has(id.trim().toLowerCase());
}

export function loadCustomCollections(): DocCollection[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw) as DocCollection[];
    return Array.isArray(parsed)
      ? parsed.filter((c) => c && typeof c.id === "string")
      : [];
  } catch {
    return [];
  }
}

function persist(collections: DocCollection[]): void {
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(collections));
  } catch {
    /* ignore quota/availability errors */
  }
}

/** Add a collection id (no-op for built-ins/dupes). Returns the updated custom list. */
export function addCustomCollection(id: string): DocCollection[] {
  const trimmed = id.trim();
  const existing = loadCustomCollections();
  if (!trimmed || isBuiltInCollection(trimmed)) return existing;
  if (existing.some((c) => c.id === trimmed)) return existing;
  const updated = [...existing, { id: trimmed, label: trimmed }];
  persist(updated);
  return updated;
}

/** Remove a custom collection from the list. Returns the updated custom list. */
export function removeCustomCollection(id: string): DocCollection[] {
  const updated = loadCustomCollections().filter((c) => c.id !== id);
  persist(updated);
  return updated;
}
