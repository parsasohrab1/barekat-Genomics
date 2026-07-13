import { useEffect, useRef } from "react";

export function usePolling<T>(
  fetcher: () => Promise<T>,
  onData: (data: T) => void,
  intervalMs = 5000,
  enabled = true
) {
  const fetcherRef = useRef(fetcher);
  const onDataRef = useRef(onData);
  fetcherRef.current = fetcher;
  onDataRef.current = onData;

  useEffect(() => {
    if (!enabled) return;

    let active = true;

    const tick = async () => {
      try {
        const data = await fetcherRef.current();
        if (active) onDataRef.current(data);
      } catch {
        /* silent on poll errors */
      }
    };

    tick();
    const id = setInterval(tick, intervalMs);
    return () => {
      active = false;
      clearInterval(id);
    };
  }, [intervalMs, enabled]);
}
