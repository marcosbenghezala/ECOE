import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

/**
 * Combina clases de Tailwind CSS de forma segura
 * Maneja conflictos de clases y permite conditional rendering
 *
 * @example
 * cn("px-2 py-1", "px-4") // => "py-1 px-4"
 * cn("text-red-500", isActive && "text-green-500") // => "text-green-500" si isActive
 */
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}
