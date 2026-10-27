import { useEffect, useState } from "react";

/** true cuando la media query coincide; se actualiza al girar o redimensionar. */
export function useMediaQuery(query: string): boolean {
  const [matches, setMatches] = useState(() => window.matchMedia(query).matches);
  useEffect(() => {
    const mql = window.matchMedia(query);
    const onChange = () => setMatches(mql.matches);
    onChange();
    mql.addEventListener("change", onChange);
    return () => mql.removeEventListener("change", onChange);
  }, [query]);
  return matches;
}

/** Mismo corte que el breakpoint `md` de Tailwind (768 px). */
export const useIsMobile = (): boolean => useMediaQuery("(max-width: 767px)");
