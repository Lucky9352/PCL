import { Link, useLocation } from "react-router-dom";
import { BarChart3, Grid3X3, Home, Layers, BookOpen } from "lucide-react";
import { cn } from "@/lib/utils";

const NAV_ITEMS = [
  { path: "/", label: "Feed", icon: Home },
  { path: "/stories", label: "Stories", icon: Layers },
  { path: "/categories", label: "Categories", icon: Grid3X3 },
  { path: "/dashboard", label: "Dashboard", icon: BarChart3 },
  { path: "/methodology", label: "How It Works", icon: BookOpen },
];

export default function Navbar() {
  const location = useLocation();

  return (
    <nav className="fixed top-0 left-0 right-0 z-50 glass">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-14">
          <Link to="/" className="flex items-center gap-2.5 group">
            <div className="w-8 h-8 rounded-lg flex items-center justify-center bg-accent">
              <span className="text-white text-sm font-black tracking-tight">IG</span>
            </div>
            <div className="flex flex-col">
              <span className="text-sm font-bold leading-none tracking-tight text-text-primary">
                IndiaGround
              </span>
              <span className="text-[9px] leading-tight tracking-widest uppercase text-(--color-text-muted)">
                News Analysis
              </span>
            </div>
          </Link>

          <div className="flex items-center gap-0.5">
            {NAV_ITEMS.map((item) => {
              const isActive = location.pathname === item.path;
              const Icon = item.icon;
              return (
                <Link
                  key={item.path}
                  to={item.path}
                  className={cn(
                    "flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors duration-150",
                    isActive
                      ? "text-accent bg-accent-muted"
                      : "text-text-secondary hover:text-text-primary hover:bg-bg-hover",
                  )}
                >
                  <Icon className="w-3.5 h-3.5" />
                  <span className="hidden sm:inline">{item.label}</span>
                </Link>
              );
            })}
          </div>
        </div>
      </div>
    </nav>
  );
}
