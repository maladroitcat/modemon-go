import { useState } from "react";
import manifest from "./data/art.json";

type ArtRecord = { urls: Record<string, string> };

function ImageAsset({ record, name, className, logo = false }: {
  record: ArtRecord; name: string; className: string; logo?: boolean;
}) {
  const [failure, setFailure] = useState(0);
  if (failure > 1) return logo ? null : <Fallback name={name} />;
  return (
    <picture className={className}>
      {failure === 0 && (
        <source type="image/webp"
          srcSet={[96, 320, 640].map((size) => `${record.urls[`webp_${size}`]} ${size}w`).join(", ")}
          sizes={logo ? "(max-width: 400px) 160px, 240px" : className === "dex-thumbnail" ? "64px" : "(max-width: 400px) 240px, 300px"}
        />
      )}
      <img src={record.urls.png_320} alt={logo ? "" : name}
        width={320} height={logo ? 160 : 320}
        loading={logo ? "eager" : "lazy"} decoding="async"
        fetchPriority={logo ? "high" : "auto"}
        onError={() => setFailure((value) => value + 1)} />
    </picture>
  );
}

export function Fallback({ name }: { name: string }) {
  return <div className="creature-fallback" aria-label={`Artwork unavailable for ${name}`}>
    <span className="fallback-symbol">?</span><strong>{name}</strong><small>Artwork unavailable</small>
  </div>;
}

export function Creature({ modemonId, name, className = "creature-art" }: {
  modemonId: string; name: string; className?: string;
}) {
  const record = (manifest.creatures as Record<string, ArtRecord>)[modemonId];
  return record ? <ImageAsset key={modemonId} record={record} name={name} className={className} /> : <Fallback name={name} />;
}

export function Brand() {
  return <h1 className="brand-title">
    <ImageAsset record={manifest.logo} name="Modémon GO" className="brand-logo" logo />
    <span>Modémon GO</span>
  </h1>;
}
