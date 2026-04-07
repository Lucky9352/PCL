export default function Footer() {
  return (
    <footer className="mt-auto border-t border-border bg-bg-secondary">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        <div className="flex flex-col sm:flex-row items-center justify-between gap-3">
          <div className="flex items-center gap-2.5">
            <div className="w-7 h-7 rounded-md flex items-center justify-center bg-accent">
              <span className="text-white text-[10px] font-black">IG</span>
            </div>
            <div>
              <p className="text-xs font-semibold text-text-primary">IndiaGround</p>
              <p className="text-[10px] text-(--color-text-muted)">
                News Bias & Fact-Check Platform
              </p>
            </div>
          </div>
          <div className="flex flex-wrap items-center gap-3 text-[11px] text-(--color-text-muted)">
            <span>BART-MNLI · RoBERTa · spaCy</span>
            <span className="hidden sm:inline">·</span>
            <span>136 sources tracked</span>
            <span className="hidden sm:inline">·</span>
            <span>Open-source research</span>
          </div>
        </div>
      </div>
    </footer>
  );
}
