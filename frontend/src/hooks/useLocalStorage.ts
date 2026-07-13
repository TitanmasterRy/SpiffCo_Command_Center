import { useEffect, useState, type Dispatch, type SetStateAction } from 'react';

/**
 * A {@link useState} whose value is mirrored to ``localStorage`` under ``key``.
 *
 * Reads the persisted value on first render (falling back to ``initial`` when
 * absent or unparseable), and writes back on every change. All storage access
 * is guarded so a disabled/full/private-mode store degrades to in-memory state
 * instead of throwing.
 */
export function useLocalStorage<T>(key: string, initial: T): [T, Dispatch<SetStateAction<T>>] {
  const [value, setValue] = useState<T>(() => readStored(key, initial));

  useEffect(() => {
    try {
      window.localStorage.setItem(key, JSON.stringify(value));
    } catch {
      /* storage unavailable or full — keep the in-memory value */
    }
  }, [key, value]);

  return [value, setValue];
}

function readStored<T>(key: string, initial: T): T {
  try {
    const raw = window.localStorage.getItem(key);
    return raw != null ? (JSON.parse(raw) as T) : initial;
  } catch {
    return initial;
  }
}
