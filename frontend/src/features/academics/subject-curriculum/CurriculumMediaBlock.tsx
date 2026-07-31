import {
  Download,
  ExternalLink,
  FileText,
  Link2,
} from "lucide-react";
import { PresentationCarousel } from "./PresentationCarousel";
import type {
  CurriculumAsset,
  CurriculumContentBlock,
} from "./model";

export function CurriculumMediaBlock({
  asset,
  block,
  onRetry,
}: {
  asset: CurriculumAsset;
  block: CurriculumContentBlock;
  onRetry?: (assetId: number) => void;
}) {
  const label = block.text || asset.title;

  if (asset.renderKind === "presentation") {
    return <PresentationCarousel asset={asset} onRetry={onRetry} />;
  }
  if (asset.renderKind === "image") {
    return (
      <figure className="overflow-hidden rounded-xl border border-border bg-background">
        <img
          src={asset.previewUrl}
          alt={label}
          loading="lazy"
          className="max-h-[34rem] w-full object-contain"
        />
        {label ? <figcaption className="border-t border-border px-3 py-2 text-xs font-bold">{label}</figcaption> : null}
      </figure>
    );
  }
  if (asset.renderKind === "video" && asset.assetKind === "file") {
    return (
      <figure className="rounded-xl border border-border bg-foreground p-2">
        <video
          src={asset.previewUrl}
          controls
          preload="metadata"
          className="aspect-video w-full rounded-lg bg-black"
        >
          Your browser does not support this lesson video.
        </video>
        {label ? <figcaption className="px-2 pb-1 pt-2 text-xs font-bold text-background">{label}</figcaption> : null}
      </figure>
    );
  }
  if (asset.renderKind === "audio") {
    return (
      <figure className="rounded-xl border border-border bg-background p-4">
        <figcaption className="mb-2 text-sm font-black">{label}</figcaption>
        <audio src={asset.previewUrl} controls preload="metadata" className="w-full">
          Your browser does not support this lesson audio.
        </audio>
      </figure>
    );
  }
  if (asset.renderKind === "embed" || (asset.renderKind === "video" && asset.assetKind !== "file")) {
    return (
      <figure className="overflow-hidden rounded-xl border border-border bg-background">
        <iframe
          src={asset.externalUrl}
          title={label}
          loading="lazy"
          allow="autoplay; encrypted-media; fullscreen; picture-in-picture; clipboard-write"
          sandbox="allow-scripts allow-same-origin allow-presentation allow-popups"
          allowFullScreen
          className="aspect-video w-full"
        />
        {label ? <figcaption className="border-t border-border px-3 py-2 text-xs font-bold">{label}</figcaption> : null}
      </figure>
    );
  }
  if (asset.renderKind === "document" && asset.mimeType === "application/pdf") {
    return (
      <section className="overflow-hidden rounded-xl border border-border bg-background">
        <iframe
          src={asset.previewUrl}
          title={label}
          className="h-[32rem] w-full"
        />
        <a
          href={asset.downloadUrl}
          className="flex min-h-11 items-center gap-2 border-t border-border px-3 text-xs font-black hover:bg-muted"
        >
          <Download className="h-4 w-4" />Download PDF
        </a>
      </section>
    );
  }
  if (asset.renderKind === "link") {
    return (
      <a
        href={asset.externalUrl}
        target="_blank"
        rel="noreferrer"
        className="flex min-h-12 items-center gap-3 rounded-xl border border-border bg-background px-4 text-sm font-black hover:border-primary/35 hover:bg-muted"
      >
        <Link2 className="h-4 w-4 text-primary" />
        <span className="min-w-0 flex-1 truncate">{label}</span>
        <ExternalLink className="h-4 w-4 text-muted-foreground" />
      </a>
    );
  }
  return (
    <a
      href={asset.downloadUrl}
      className="flex min-h-12 items-center gap-3 rounded-xl border border-border bg-background px-4 text-sm font-black hover:border-primary/35 hover:bg-muted"
    >
      <FileText className="h-4 w-4 text-primary" />
      <span className="min-w-0 flex-1 truncate">{label}</span>
      <Download className="h-4 w-4 text-muted-foreground" />
    </a>
  );
}
