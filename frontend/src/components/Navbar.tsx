import { Link, useLocation } from "react-router-dom";
import { Shield, BarChart3, Grid3X3, Home } from "lucide-react";
import { cn } from "@/lib/utils";

const NAV_ITEMS = [
  { path: "/", label: "Feed", icon: Home },
  { path: "/categories", label: "Categories", icon: Grid3X3 },
  { path: "/dashboard", label: "Dashboard", icon: BarChart3 },
];

export default function Navbar() {
  const location = useLocation();

  return (
    <nav className="fixed top-0 left-0 right-0 z-50 glass">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo */}
          <Link to="/" className="flex items-center gap-3 group">
            <div
              className="w-9 h-9 rounded-lg flex items-center justify-center transition-all duration-300 group-hover:scale-110"
              style={{
                background: "var(--gradient-hero)",
                boxShadow: "0 0 20px var(--color-accent-glow)",
              }}
            >
              <Shield className="w-5 h-5 text-white" />
            </div>
            <div className="flex flex-col">
              <span
                className="text-lg font-bold leading-tight"
                style={{
                  background: "var(--gradient-hero)",
                  WebkitBackgroundClip: "text",
                  WebkitTextFillColor: "transparent",
                }}
              >
                IndiaGround
              </span>
              <span
                className="text-[10px] leading-tight tracking-widest uppercase"
                style={{ color: "var(--color-text-muted)" }}
              >
                News Bias & Fact Check
              </span>
            </div>
          </Link>

          {/* Nav links */}
          <div className="flex items-center gap-1">
            {NAV_ITEMS.map((item) => {
              const isActive = location.pathname === item.path;
              const Icon = item.icon;
              return (
                <Link
                  key={item.path}
                  to={item.path}
                  className={cn(
                    "flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all duration-200",
                    isActive ? "text-white" : "hover:text-white",
                  )}
                  style={{
                    color: isActive ? "var(--color-text-primary)" : "var(--color-text-secondary)",
                    background: isActive ? "rgba(99, 102, 241, 0.15)" : "transparent",
                    border: isActive
                      ? "1px solid rgba(99, 102, 241, 0.3)"
                      : "1px solid transparent",
                  }}
                >
                  <Icon className="w-4 h-4" />
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
