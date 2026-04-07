import { useState } from "react";
import { useInfiniteQuery } from "@tanstack/react-query";
import { fetchArticles, triggerScrape } from "@/api/client";
import ArticleCard from "@/components/ArticleCard";
import { Search, RefreshCw, Loader2 } from "lucide-react";

const FILTERS = [
  { label: "All", value: "" },
  { label: "Politics", value: "politics" },
  { label: "Business", value: "business" },
  { label: "Sports", value: "sports" },
  { label: "Technology", value: "technology" },
  { label: "World", value: "world" },
  { label: "Science", value: "science" },
  { label: "Entertainment", value: "entertainment" },
];

export default function Home() {
  const [category, setCategory] = useState("");
  const [search, setSearch] = useState("");
  const [searchInput, setSearchInput] = useState("");
  const [isScraping, setIsScraping] = useState(false);

  const { data, isLoading, error, fetchNextPage, hasNextPage, isFetchingNextPage, refetch } =
    useInfiniteQuery({
      queryKey: ["articles", category, search],
      queryFn: ({ pageParam }) =>
        fetchArticles({
          page_size: 30,
          cursor: (pageParam as string) || undefined,
          category: category || undefined,
          search: search || undefined,
        }),
      initialPageParam: undefined,
      getNextPageParam: (lastPage) => lastPage.meta.next_cursor ?? undefined,
    });

  const allArticles = data?.pages.flatMap((page) => page.data) ?? [];
  const totalCount = data?.pages[0]?.meta.total_count ?? 0;

  const handleScrape = async () => {
    setIsScraping(true);
    try {
      await triggerScrape();
      setTimeout(() => {
        refetch();
        setIsScraping(false);
      }, 3000);
    } catch {
      setIsScraping(false);
    }
  };

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setSearch(searchInput);
  };

  return (
    <div className="animate-fade-in">
      {/* Hero section */}
      <div className="text-center mb-10">
        <h1
          className="text-4xl sm:text-5xl font-extrabold mb-3"
          style={{
            background: "var(--gradient-hero)",
            WebkitBackgroundClip: "text",
            WebkitTextFillColor: "transparent",
          }}
        >
          IndiaGround
        </h1>
        <p className="text-lg max-w-xl mx-auto" style={{ color: "var(--color-text-secondary)" }}>
          Automated news bias detection & fact-checking for Indian media
        </p>
      </div>

      {/* Search + Controls */}
      <div className="flex flex-col sm:flex-row gap-3 mb-6">
        {/* Search */}
        <form onSubmit={handleSearch} className="flex-1 relative">
          <Search
            className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4"
            style={{ color: "var(--color-text-muted)" }}
          />
          <input
            type="text"
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            placeholder="Search articles..."
            className="w-full pl-11 pr-4 py-3 rounded-xl text-sm outline-none transition-all duration-200 focus:ring-2"
            style={
              {
                background: "var(--color-bg-card)",
                color: "var(--color-text-primary)",
                border: "1px solid var(--color-border)",
                "--tw-ring-color": "var(--color-accent)",
              } as React.CSSProperties
            }
          />
        </form>

        {/* Scrape trigger */}
        <button
          onClick={handleScrape}
          disabled={isScraping}
          className="flex items-center gap-2 px-5 py-3 rounded-xl text-sm font-medium transition-all duration-200 hover:opacity-90 disabled:opacity-50"
          style={{
            background: "var(--gradient-hero)",
            color: "white",
            boxShadow: "0 0 20px var(--color-accent-glow)",
          }}
        >
          {isScraping ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            <RefreshCw className="w-4 h-4" />
          )}
          {isScraping ? "Scraping..." : "Scrape Now"}
        </button>
      </div>

      {/* Category filters */}
      <div className="flex flex-wrap gap-2 mb-8">
        {FILTERS.map((f) => (
          <button
            key={f.value}
            onClick={() => setCategory(f.value)}
            className="px-4 py-2 rounded-lg text-xs font-semibold uppercase tracking-wider transition-all duration-200"
            style={{
              background:
                category === f.value ? "rgba(99, 102, 241, 0.15)" : "var(--color-bg-card)",
              color: category === f.value ? "var(--color-accent)" : "var(--color-text-secondary)",
              border:
                category === f.value
                  ? "1px solid rgba(99, 102, 241, 0.3)"
                  : "1px solid var(--color-border)",
            }}
          >
            {f.label}
          </button>
        ))}
      </div>

      {/* Articles grid */}
      {isLoading ? (
        <div className="flex items-center justify-center py-20">
          <Loader2 className="w-8 h-8 animate-spin" style={{ color: "var(--color-accent)" }} />
        </div>
      ) : error ? (
        <div
          className="text-center py-20 rounded-2xl"
          style={{ background: "var(--color-bg-card)" }}
        >
          <p className="text-lg font-medium mb-2" style={{ color: "var(--color-red)" }}>
            Failed to load articles
          </p>
          <p className="text-sm mb-4" style={{ color: "var(--color-text-muted)" }}>
            Make sure the backend is running on port 8000
          </p>
          <button
            onClick={() => refetch()}
            className="px-4 py-2 rounded-lg text-sm font-medium"
            style={{
              background: "rgba(99, 102, 241, 0.15)",
              color: "var(--color-accent)",
              border: "1px solid rgba(99, 102, 241, 0.3)",
            }}
          >
            Retry
          </button>
        </div>
      ) : allArticles.length === 0 ? (
        <div
          className="text-center py-20 rounded-2xl"
          style={{ background: "var(--color-bg-card)" }}
        >
          <p className="text-lg font-medium mb-2" style={{ color: "var(--color-text-primary)" }}>
            No articles yet
          </p>
          <p className="text-sm mb-4" style={{ color: "var(--color-text-muted)" }}>
            Click "Scrape Now" to fetch articles from Inshorts
          </p>
        </div>
      ) : (
        <>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 stagger-children">
            {allArticles.map((article, i) => (
              <ArticleCard key={article.id} article={article} index={i} />
            ))}
          </div>

          {/* Pagination info and Load More */}
          <div className="mt-12 flex flex-col items-center gap-4">
            <p className="text-sm" style={{ color: "var(--color-text-muted)" }}>
              Showing {allArticles.length} of {totalCount} articles
            </p>

            {hasNextPage && (
              <button
                onClick={() => fetchNextPage()}
                disabled={isFetchingNextPage}
                className="px-8 py-3 rounded-xl text-sm font-semibold transition-all duration-200 hover:scale-105 disabled:opacity-50 disabled:hover:scale-100"
                style={{
                  background: "var(--color-bg-card)",
                  color: "var(--color-accent)",
                  border: "1px solid var(--color-border)",
                  boxShadow: "0 4px 12px rgba(0,0,0,0.1)",
                }}
              >
                {isFetchingNextPage ? (
                  <div className="flex items-center gap-2">
                    <Loader2 className="w-4 h-4 animate-spin" />
                    <span>Loading more...</span>
                  </div>
                ) : (
                  "Show More Articles"
                )}
              </button>
            )}
          </div>
        </>
      )}
    </div>
  );
}
