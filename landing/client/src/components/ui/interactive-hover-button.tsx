import React from "react";
import { ArrowRight } from "lucide-react";
import { cn } from "@/lib/utils";

interface InteractiveHoverButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  text?: string;
}

const InteractiveHoverButton = React.forwardRef<
  HTMLButtonElement,
  InteractiveHoverButtonProps
>(({ text = "Button", className, ...props }, ref) => {
  return (
    <button
      ref={ref}
      className={cn(
        "group relative cursor-pointer overflow-hidden rounded-full border bg-background text-center font-semibold inline-flex items-center justify-center",
        className,
      )}
      {...props}
    >
      {/* Initial text */}
      <span className="relative z-20 inline-block translate-x-0 transition-all duration-300 group-hover:translate-x-12 group-hover:opacity-0 whitespace-nowrap">
        {text}
      </span>
      
      {/* Text with arrow on hover */}
      <div className="absolute top-0 z-10 flex h-full w-full translate-x-12 items-center justify-center gap-2 opacity-0 transition-all duration-300 group-hover:-translate-x-0 group-hover:opacity-100">
        <span className="text-inherit whitespace-nowrap">{text}</span>
        <ArrowRight className="w-4 h-4 text-inherit flex-shrink-0" />
      </div>
    </button>
  );
});

InteractiveHoverButton.displayName = "InteractiveHoverButton";

export { InteractiveHoverButton };

