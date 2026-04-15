import { useEffect, useRef, useState } from "react";

interface UseLazyVisibleOptions {
  rootMargin?: string;
}

export function useLazyVisible(options: UseLazyVisibleOptions = {}) {
  const { rootMargin = "100px" } = options;
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

    return () => observer.disconnect();
  }, [rootMargin, visible]);

  return { ref, visible };
}
