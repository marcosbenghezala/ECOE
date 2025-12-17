import { cn } from "@/lib/utils"

export function UMHLogo({ className = "" }: { className?: string }) {
  return (
    <div className={cn("flex items-center gap-3", className)}>
      <img
        src="/images/logo-umh.png"
        alt="Universidad Miguel Hernández"
        className="h-12 w-auto rounded-lg"
      />
      <span className="text-base font-semibold text-foreground leading-tight">
        Universidad Miguel Hernández
      </span>
    </div>
  )
}
