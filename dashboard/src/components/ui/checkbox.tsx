import { cn } from "@/lib/utils";
import { IconCheck } from "@tabler/icons-react";
import * as React from "react";

const Checkbox = React.forwardRef<
    HTMLInputElement,
    Omit<React.InputHTMLAttributes<HTMLInputElement>, "onChange"> & {
        onCheckedChange?: (checked: boolean) => void;
    }
>(({ className, onCheckedChange, ...props }, ref) => {
    return (
        <div className="relative flex items-center justify-center">
            <input
                type="checkbox"
                className={cn(
                    "peer h-4 w-4 shrink-0 appearance-none rounded-sm border border-neutral-200 border-neutral-900 shadow checked:bg-neutral-900 checked:text-neutral-50 focus-visible:ring-1 focus-visible:ring-neutral-950 focus-visible:outline-none disabled:cursor-not-allowed disabled:opacity-50 dark:border-neutral-500 dark:checked:border-green-600 dark:checked:bg-green-600",
                    "cursor-pointer",
                    className,
                )}
                onChange={(e) => onCheckedChange?.(e.target.checked)}
                ref={ref}
                {...props}
            />
            <IconCheck className="pointer-events-none absolute h-3 w-3 text-white opacity-0 peer-checked:opacity-100" />
        </div>
    );
});
Checkbox.displayName = "Checkbox";

export { Checkbox };
