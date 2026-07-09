import { useEffect, useRef, useState } from "react";

interface UseLazyVisibleOptions {
  rootMargin?: string;
  /**
   * Safety-net delay (ms) after which visibility is forced on even if the
   * IntersectionObserver never reports an intersection. Several mobile
   * WebViews (notably Telegram's in-app browser) are known to silently drop
   * IntersectionObserver callbacks for targets nested inside a scrollable
   * ancestor other than the document body, which otherwise leaves this
   * content stuck behind its loading skeleton forever. Set to 0 to disable.
   */
  fallbackDelay?: number;
}

export function useLazyVisible(options: UseLazyVisibleOptions = {}) {
  const { rootMargin = "100px", fallbackDelay = 600 } = options;
  const ref = useRef<HTMLDivElement>(null);
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    if (visible) {
      return;
    }
    const target = ref.current;
    if (!target) {
      return;
    }
    if (typeof window.IntersectionObserver === "undefined") {
      setVisible(true);
      return;
    }

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setVisible(true);
          observer.disconnect();
        }
      },
      { rootMargin }
    );
    observer.observe(target);

    const fallbackTimer = fallbackDelay > 0 ? window.setTimeout(() => setVisible(true), fallbackDelay) : 0;

    return () => {
      observer.disconnect();
      if (fallbackTimer) window.clearTimeout(fallbackTimer);
    };
  }, [rootMargin, fallbackDelay, visible]);

  return { ref, visible };
}
