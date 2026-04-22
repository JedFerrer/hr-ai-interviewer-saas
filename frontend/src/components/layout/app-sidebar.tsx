"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Home,
  Briefcase,
  Settings,
  LogOut,
  LayoutGrid,
} from "lucide-react";

import { cn } from "@/lib/utils";
import { useAuth } from "@/lib/auth";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";

const NAV_ITEMS = [
  { label: "Dashboard", href: "/dashboard", icon: Home },
  { label: "Jobs", href: "/dashboard/jobs", icon: Briefcase },
  { label: "Settings", href: "/dashboard/settings", icon: Settings },
];

interface AppSidebarProps {
  isCollapsed: boolean;
  onToggle?: () => void;
}

export function AppSidebar({ isCollapsed, onToggle }: AppSidebarProps) {
  const { logout } = useAuth();
  const currentPath = usePathname();

  return (
    <aside
      className={cn(
        "relative flex h-full flex-col border-r bg-sidebar-background text-sidebar-foreground transition-all duration-300",
        isCollapsed ? "w-[68px]" : "w-[260px]",
      )}
    >
      {/* Logo / Brand */}
      <div className="flex h-16 items-center gap-3 border-b px-4">
        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-primary text-primary-foreground">
          <LayoutGrid className="h-4 w-4" />
        </div>
        {!isCollapsed && (
          <span className="text-sm font-bold tracking-tight">HireAI</span>
        )}
      </div>

      <ScrollArea className="flex-1 py-4">
        <nav className="flex flex-col gap-1 px-3">
          {NAV_ITEMS.map((item) => {
            const isActive =
              item.href === "/dashboard"
                ? currentPath === "/dashboard" || currentPath === "/dashboard/"
                : currentPath.startsWith(item.href);
            const Icon = item.icon;

            const link = (
              <Link
                href={item.href}
                className={cn(
                  "flex items-center gap-3 rounded-md px-2 py-2 text-sm font-medium transition-colors",
                  "hover:bg-sidebar-accent hover:text-sidebar-accent-foreground",
                  isActive &&
                    "bg-sidebar-accent text-sidebar-accent-foreground font-semibold",
                )}
              >
                <span className="shrink-0">
                  <Icon className="h-4 w-4" />
                </span>
                {!isCollapsed && (
                  <span className="truncate">{item.label}</span>
                )}
              </Link>
            );

            if (isCollapsed) {
              return (
                <Tooltip key={item.href} delayDuration={0}>
                  <TooltipTrigger asChild>{link}</TooltipTrigger>
                  <TooltipContent side="right" className="font-medium">
                    {item.label}
                  </TooltipContent>
                </Tooltip>
              );
            }

            return <div key={item.href}>{link}</div>;
          })}
        </nav>
      </ScrollArea>

      {/* Bottom: Sign out */}
      <div className="border-t px-3 py-3">
        <Tooltip delayDuration={0}>
          <TooltipTrigger asChild>
            <button
              className={cn(
                "flex w-full items-center gap-3 rounded-md px-2 py-2 text-sm font-medium transition-colors",
                "hover:bg-sidebar-accent hover:text-sidebar-accent-foreground",
              )}
              onClick={logout}
              aria-label="Sign out"
            >
              <span className="shrink-0">
                <LogOut className="h-4 w-4" />
              </span>
              {!isCollapsed && <span className="truncate">Sign Out</span>}
            </button>
          </TooltipTrigger>
          {isCollapsed && (
            <TooltipContent side="right" className="font-medium">
              Sign Out
            </TooltipContent>
          )}
        </Tooltip>
      </div>
    </aside>
  );
}
