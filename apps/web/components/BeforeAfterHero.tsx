"use client";

import { PointerEvent, useEffect, useRef, useState } from "react";

export type HeroMode = "upload" | "floorplan" | "brief" | "options" | "renders";

type Position = {
  x: number;
  y: number;
};

type HeroImagePair = {
  beforeSrc: string;
  afterSrc: string;
  beforeAlt: string;
  afterAlt: string;
};

const INITIAL_POSITION: Position = { x: 63, y: 56 };

const heroImagePairs: Record<HeroMode, HeroImagePair> = {
  upload: {
    beforeSrc: "/images/hero-sets/upload-before.png",
    afterSrc: "/images/hero-sets/upload-after.png",
    beforeAlt: "上传前的空房客厅",
    afterAlt: "上传后生成家具布置的客厅"
  },
  floorplan: {
    beforeSrc: "/images/hero-sets/floorplan-before.png",
    afterSrc: "/images/hero-sets/floorplan-after.png",
    beforeAlt: "校正前的空房卧室",
    afterAlt: "校正后生成家具布置的卧室"
  },
  brief: {
    beforeSrc: "/images/hero-sets/brief-before.png",
    afterSrc: "/images/hero-sets/brief-after.png",
    beforeAlt: "需求填写前的空房餐厨空间",
    afterAlt: "需求填写后生成家具布置的餐厨空间"
  },
  options: {
    beforeSrc: "/images/hero-sets/options-before.png",
    afterSrc: "/images/hero-sets/options-after.png",
    beforeAlt: "方案生成前的空房书房",
    afterAlt: "方案生成后生成家具布置的书房"
  },
  renders: {
    beforeSrc: "/images/hero-sets/renders-before.png",
    afterSrc: "/images/hero-sets/renders-after.png",
    beforeAlt: "渲染前的空房家庭客厅",
    afterAlt: "渲染后生成家具布置的家庭客厅"
  }
};

const preloadSources = Object.values(heroImagePairs).flatMap((pair) => [
  pair.beforeSrc,
  pair.afterSrc
]);

export function BeforeAfterHero({
  className = "",
  interactive = true,
  mode = "upload"
}: {
  className?: string;
  interactive?: boolean;
  mode?: HeroMode;
}) {
  const frameRef = useRef<HTMLDivElement | null>(null);
  const [position, setPosition] = useState<Position>(INITIAL_POSITION);
  const [active, setActive] = useState(false);
  const pair = heroImagePairs[mode];

  useEffect(() => {
    setPosition(INITIAL_POSITION);
    setActive(false);
  }, [mode]);

  function moveReveal(event: PointerEvent<HTMLDivElement>) {
    if (!interactive || !frameRef.current) return;
    const rect = frameRef.current.getBoundingClientRect();
    const x = ((event.clientX - rect.left) / rect.width) * 100;
    const y = ((event.clientY - rect.top) / rect.height) * 100;

    setPosition({
      x: Math.max(0, Math.min(100, x)),
      y: Math.max(0, Math.min(100, y))
    });
  }

  const radius = active ? "280px" : "0px";
  const mask = `radial-gradient(circle ${radius} at ${position.x}% ${position.y}%, #000 0%, #000 58%, rgba(0,0,0,0.72) 70%, rgba(0,0,0,0) 100%)`;

  return (
    <div
      ref={frameRef}
      className={`relative h-full w-full overflow-hidden bg-cloud ${className}`}
      onPointerEnter={() => setActive(true)}
      onPointerLeave={() => setActive(false)}
      onPointerCancel={() => setActive(false)}
      onPointerMove={moveReveal}
      onPointerDown={(event) => {
        setActive(true);
        moveReveal(event);
      }}
    >
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img
        key={`${mode}-before`}
        src={pair.beforeSrc}
        alt={pair.beforeAlt}
        className="h-full w-full object-cover"
        draggable={false}
      />
      <div
        key={`${mode}-after`}
        className="absolute inset-0"
        style={{
          WebkitMaskImage: mask,
          maskImage: mask,
          WebkitMaskRepeat: "no-repeat",
          maskRepeat: "no-repeat",
          willChange: "mask-image"
        }}
      >
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src={pair.afterSrc}
          alt={pair.afterAlt}
          className="h-full w-full object-cover"
          draggable={false}
        />
      </div>
      <div className="pointer-events-none absolute inset-0 bg-gradient-to-r from-white/70 via-white/14 to-white/0" />
      <div className="pointer-events-none absolute inset-x-0 bottom-0 h-40 bg-gradient-to-t from-ink/18 to-transparent" />
      <div aria-hidden="true" className="pointer-events-none absolute h-0 w-0 overflow-hidden opacity-0">
        {preloadSources.map((src) => (
          // eslint-disable-next-line @next/next/no-img-element
          <img key={src} src={src} alt="" draggable={false} />
        ))}
      </div>
    </div>
  );
}
