"use client";

import { cn } from "@/lib/utils";
import React, { ReactNode } from "react";

interface AuroraBackgroundProps extends React.HTMLProps<HTMLDivElement> {
  children: ReactNode;
  showRadialGradient?: boolean;
}

export const AuroraBackground = ({
  className,
  children,
  showRadialGradient = true,
  ...props
}: AuroraBackgroundProps) => {
  return (
    <div
      className={cn(
        "relative flex flex-col h-full w-full items-center justify-center transition-bg",
        className
      )}
      {...props}
    >
      <div className="absolute inset-0 overflow-hidden">
        {/* Main Aurora Layer - More Visible */}
        <div
          className={cn(
            `
            absolute inset-0
            [--aurora:repeating-linear-gradient(100deg,var(--blue-400)_10%,var(--cyan-400)_15%,var(--indigo-400)_20%,var(--purple-400)_25%,var(--violet-400)_30%)]
            [background-image:var(--aurora)]
            [background-size:400%,_400%]
            [background-position:0%_0%]
            animate-aurora-fast
            opacity-30
            blur-[40px]
            will-change-transform
            pointer-events-none
            `,
            showRadialGradient &&
              `[mask-image:radial-gradient(ellipse_at_center,black_30%,transparent_70%)]`
          )}
        />
        
        {/* Secondary Aurora Layer - Different direction for depth */}
        <div
          className={cn(
            `
            absolute inset-0
            [--aurora-2:repeating-linear-gradient(100deg,var(--purple-500)_10%,var(--pink-400)_15%,var(--rose-400)_20%,var(--indigo-500)_25%,var(--blue-500)_30%)]
            [background-image:var(--aurora-2)]
            [background-size:300%,_300%]
            [background-position:100%_100%]
            animate-aurora
            opacity-25
            blur-[50px]
            will-change-transform
            pointer-events-none
            mix-blend-soft-light
            `,
            showRadialGradient &&
              `[mask-image:radial-gradient(ellipse_at_center,black_20%,transparent_80%)]`
          )}
        />
      </div>
      {children}
    </div>
  );
};

