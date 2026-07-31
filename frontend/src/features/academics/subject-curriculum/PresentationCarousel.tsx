import { useEffect, useRef, useState, type RefObject } from "react";
import {
  ChevronLeft,
  ChevronRight,
  Download,
  Expand,
  LoaderCircle,
  RefreshCcw,
  X,
} from "lucide-react";
import type { CurriculumAsset } from "./model";

function SlideDeck({
  asset,
  fullscreen,
  onFullscreen,
  openButtonRef,
}: {
  asset: CurriculumAsset;
  fullscreen: boolean;
  onFullscreen: (open: boolean) => void;
  openButtonRef?: RefObject<HTMLButtonElement>;
}) {
  const [slideIndex, setSlideIndex] = useState(0);
  const closeButtonRef = useRef<HTMLButtonElement>(null);
  const slides = asset.slides;
  const slide = slides[slideIndex];

  useEffect(() => {
    setSlideIndex(0);
  }, [asset.assetId, slides.length]);

  useEffect(() => {
    if (!fullscreen) return undefined;
    closeButtonRef.current?.focus();
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") onFullscreen(false);
      if (event.key === "ArrowLeft") {
        setSlideIndex((current) => Math.max(0, current - 1));
      }
      if (event.key === "ArrowRight") {
        setSlideIndex((current) => Math.min(slides.length - 1, current + 1));
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [fullscreen, onFullscreen, slides.length]);

  if (!slide) return null;
  return (
    <section
      className={
        fullscreen
          ? "fixed inset-0 z-[90] flex flex-col bg-foreground/95 p-3 text-background sm:p-5"
          : "overflow-hidden rounded-xl border border-border bg-background"
      }
      aria-label={`${asset.title} slideshow`}
    >
      <header
        className={`flex items-center gap-2 ${
          fullscreen ? "pb-3" : "border-b border-border px-3 py-2"
        }`}
      >
        <p className="min-w-0 flex-1 truncate text-sm font-black">{asset.title}</p>
        <span className="text-xs font-bold tabular-nums" aria-live="polite">
          {slideIndex + 1} / {slides.length}
        </span>
        {fullscreen ? (
          <button
            ref={closeButtonRef}
            type="button"
            onClick={() => onFullscreen(false)}
            className="flex h-10 w-10 items-center justify-center rounded-lg hover:bg-background/15 focus:outline-none focus-visible:ring-2 focus-visible:ring-background"
            aria-label="Close fullscreen slideshow"
          >
            <X className="h-5 w-5" />
          </button>
        ) : (
          <button
            ref={openButtonRef}
            type="button"
            onClick={() => onFullscreen(true)}
            className="flex h-10 w-10 items-center justify-center rounded-lg hover:bg-muted focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/35"
            aria-label="Open fullscreen slideshow"
          >
            <Expand className="h-4 w-4" />
          </button>
        )}
      </header>

      <div className={`relative flex min-h-0 flex-1 items-center justify-center ${
        fullscreen ? "" : "aspect-video bg-foreground/5"
      }`}>
        <img
          src={slide.previewUrl}
          alt={`${asset.title}, slide ${slide.slideNumber}`}
          className={fullscreen ? "max-h-full max-w-full object-contain" : "h-full w-full object-contain"}
        />
        <button
          type="button"
          disabled={slideIndex === 0}
          onClick={() => setSlideIndex((current) => Math.max(0, current - 1))}
          className="absolute left-2 flex h-11 w-11 items-center justify-center rounded-full border border-border/60 bg-background/90 text-foreground shadow-lg disabled:opacity-30"
          aria-label="Previous slide"
        >
          <ChevronLeft className="h-5 w-5" />
        </button>
        <button
          type="button"
          disabled={slideIndex === slides.length - 1}
          onClick={() =>
            setSlideIndex((current) => Math.min(slides.length - 1, current + 1))
          }
          className="absolute right-2 flex h-11 w-11 items-center justify-center rounded-full border border-border/60 bg-background/90 text-foreground shadow-lg disabled:opacity-30"
          aria-label="Next slide"
        >
          <ChevronRight className="h-5 w-5" />
        </button>
      </div>

      <div className={`flex gap-2 overflow-x-auto ${fullscreen ? "pt-3" : "border-t border-border p-2"}`}>
        {slides.map((candidate, index) => (
          <button
            key={candidate.renditionId}
            type="button"
            onClick={() => setSlideIndex(index)}
            aria-label={`Open slide ${candidate.slideNumber}`}
            aria-current={index === slideIndex ? "true" : undefined}
            className={`h-14 w-24 shrink-0 overflow-hidden rounded-md border-2 ${
              index === slideIndex ? "border-primary" : "border-transparent opacity-65"
            }`}
          >
            <img
              src={candidate.previewUrl}
              alt=""
              loading="lazy"
              className="h-full w-full object-cover"
            />
          </button>
        ))}
      </div>
    </section>
  );
}

export function PresentationCarousel({
  asset,
  onRetry,
}: {
  asset: CurriculumAsset;
  onRetry?: (assetId: number) => void;
}) {
  const [fullscreen, setFullscreen] = useState(false);
  const openButtonRef = useRef<HTMLButtonElement>(null);
  const wasFullscreen = useRef(false);

  useEffect(() => {
    if (wasFullscreen.current && !fullscreen) {
      openButtonRef.current?.focus();
    }
    wasFullscreen.current = fullscreen;
    if (!fullscreen) return undefined;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = previousOverflow;
    };
  }, [fullscreen]);

  if (asset.conversionStatus === "pending" || asset.conversionStatus === "processing") {
    return (
      <div className="rounded-xl border border-primary/20 bg-primary/5 p-4">
        <div className="flex items-center gap-2 text-primary">
          <LoaderCircle className="h-4 w-4 animate-spin motion-reduce:animate-none" />
          <p className="text-sm font-black">Preparing slideshow…</p>
        </div>
        <p className="mt-1 text-xs text-muted-foreground">
          The original presentation is safely stored while slides are converted.
        </p>
        <a
          href={asset.downloadUrl}
          className="mt-3 inline-flex min-h-10 items-center gap-2 rounded-lg border border-border bg-surface px-3 text-xs font-black"
        >
          <Download className="h-4 w-4" />Original PowerPoint
        </a>
      </div>
    );
  }
  if (asset.conversionStatus === "failed") {
    return (
      <div role="alert" className="rounded-xl border border-destructive/25 bg-destructive/5 p-4">
        <p className="text-sm font-black text-destructive">Slideshow conversion failed</p>
        <p className="mt-1 text-xs text-muted-foreground">
          {asset.conversionError || "Check the PowerPoint file and try again."}
        </p>
        <div className="mt-3 flex flex-wrap gap-2">
          {onRetry ? (
            <button
              type="button"
              onClick={() => onRetry(asset.assetId)}
              className="inline-flex min-h-10 items-center gap-2 rounded-lg border border-border bg-surface px-3 text-xs font-black"
            >
              <RefreshCcw className="h-4 w-4" />Retry conversion
            </button>
          ) : null}
          <a
            href={asset.downloadUrl}
            className="inline-flex min-h-10 items-center gap-2 rounded-lg border border-border bg-surface px-3 text-xs font-black"
          >
            <Download className="h-4 w-4" />Original PowerPoint
          </a>
        </div>
      </div>
    );
  }
  if (!asset.slides.length) {
    return (
      <a
        href={asset.downloadUrl}
        className="inline-flex min-h-11 items-center gap-2 rounded-lg border border-border px-3 text-sm font-black"
      >
        <Download className="h-4 w-4" />Download presentation
      </a>
    );
  }
  return (
    <>
      <SlideDeck
        asset={asset}
        fullscreen={false}
        onFullscreen={setFullscreen}
        openButtonRef={openButtonRef}
      />
      {fullscreen ? (
        <SlideDeck asset={asset} fullscreen onFullscreen={setFullscreen} />
      ) : null}
      <a
        href={asset.downloadUrl}
        className="mt-2 inline-flex min-h-10 items-center gap-2 rounded-lg border border-border px-3 text-xs font-black hover:bg-muted"
      >
        <Download className="h-4 w-4" />Original PowerPoint
      </a>
    </>
  );
}
