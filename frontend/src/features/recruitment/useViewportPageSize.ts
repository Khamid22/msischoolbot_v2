import { useEffect, useState, type RefObject } from "react";

export function useViewportPageSize(
  anchorRef: RefObject<HTMLElement | null>,
  rowHeight = 58,
  footerHeight = 62,
) {
  const [perPage, setPerPage] = useState(() => (window.innerWidth < 768 ? 5 : 10));

  useEffect(() => {
    let frame = 0;
    const calculate = () => {
      window.cancelAnimationFrame(frame);
      frame = window.requestAnimationFrame(() => {
        if (window.innerWidth < 768) {
          setPerPage(5);
          return;
        }
        const top = anchorRef.current?.getBoundingClientRect().top ?? 280;
        const available = Math.max(rowHeight * 5, window.innerHeight - top - footerHeight - 12);
        setPerPage(Math.max(5, Math.min(50, Math.floor(available / rowHeight))));
      });
    };
    calculate();
    window.addEventListener("resize", calculate);
    const observer = new ResizeObserver(calculate);
    observer.observe(document.documentElement);
    if (anchorRef.current) observer.observe(anchorRef.current);
    return () => {
      window.cancelAnimationFrame(frame);
      window.removeEventListener("resize", calculate);
      observer.disconnect();
    };
  }, [anchorRef, footerHeight, rowHeight]);

  return perPage;
}
