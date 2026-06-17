import { useState, useRef } from 'react';

interface Props {
  src: string;
  previewSrc?: string;
  alt?: string;
  thumbnailSize?: number;
  previewSize?: number;
}

export default function OwnerclanHoverImage({ src, previewSrc, alt = '', thumbnailSize = 40, previewSize = 360 }: Props) {
  const big = previewSrc || src;
  const [hover, setHover] = useState(false);
  const [pos, setPos] = useState<{ x: number; y: number } | null>(null);
  const ref = useRef<HTMLImageElement>(null);

  const onMove = (e: React.MouseEvent) => {
    setPos({ x: e.clientX, y: e.clientY });
  };

  if (!src) {
    return (
      <div
        className="rounded bg-gray-700/30"
        style={{ width: thumbnailSize, height: thumbnailSize }}
      />
    );
  }

  return (
    <>
      <img
        ref={ref}
        src={src}
        alt={alt}
        loading="lazy"
        className="rounded object-cover cursor-zoom-in"
        style={{ width: thumbnailSize, height: thumbnailSize }}
        onMouseEnter={() => setHover(true)}
        onMouseLeave={() => setHover(false)}
        onMouseMove={onMove}
      />
      {hover && pos && (
        <div
          className="fixed z-[9999] pointer-events-none transition-opacity duration-150"
          style={{
            left: Math.min(pos.x + 16, window.innerWidth - previewSize - 8),
            top: Math.min(pos.y + 16, window.innerHeight - previewSize - 8),
          }}
        >
          <img
            src={big}
            alt={alt}
            className="rounded-lg border border-gray-600 shadow-2xl bg-white"
            style={{ width: previewSize, height: previewSize, objectFit: 'contain' }}
          />
        </div>
      )}
    </>
  );
}
