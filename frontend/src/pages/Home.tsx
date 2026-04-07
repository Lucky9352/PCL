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
      queryFn: ({ pageParam }: { pageParam: string | undefined }) =>
        fetchArticles({
          page_size: 30,
          cursor: pageParam || undefined,
          category: category || undefined,
          search: search || undefined,
        }),
      initialPageParam: undefined as string | undefined,
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
      {/* Hero */}
      <div className="mb-8">
        <h1 className="text-3xl sm:text-4xl font-extrabold tracking-tight mb-1 text-text-primary">
          IndiaGround
        </h1>
        <p className="text-sm sm:text-base text-text-secondary">
          Automated news bias detection & fact-checking for Indian media
        </p>
      </div>

      {/* Search + Scrape */}
      <div className="flex flex-col sm:flex-row gap-2.5 mb-5">
        <form onSubmit={handleSearch} className="flex-1 relative">
          <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-(--color-text-muted)" />
          <input
            type="text"
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            placeholder="Search articles..."
            className="w-full pl-10 pr-4 py-2.5 rounded-lg text-sm outline-none transition-colors duration-150
                       bg-bg-card text-text-primary
                       border border-border focus:border-accent"
          />
        </form>

        <button
          onClick={handleScrape}
          disabled={isScraping}
          className="flex items-center justify-center gap-2 px-5 py-2.5 rounded-lg text-sm font-medium
                     bg-accent text-white transition-colors duration-150
                     hover:bg-accent-hover disabled:opacity-50"
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
      <div className="flex flex-wrap gap-1.5 mb-7">
        {FILTERS.map((f) => (
          <button
            key={f.value}
            onClick={() => setCategory(f.value)}
            className={`px-3 py-1.5 rounded-md text-xs font-medium transition-colors duration-150 ${
              category === f.value
                ? "bg-accent-muted text-accent border border-accent-border"
                : "bg-bg-card text-text-secondary border border-border hover:text-text-primary"
            }`}
          >
            {f.label}
          </button>
        ))}
      </div>

      {/* Articles grid */}
      {isLoading ? (
        <div className="flex items-center justify-center py-20">
          <Loader2 className="w-6 h-6 animate-spin text-accent" />
        </div>
      ) : error ? (
        <div className="text-center py-20 rounded-xl bg-bg-card border border-border">
          <p className="text-sm font-medium mb-2 text-(--color-red)">Failed to load articles</p>
          <p className="text-xs mb-4 text-(--color-text-muted)">
            Make sure the backend is running on port 8000
          </p>
          <button
            onClick={() => refetch()}
            className="px-4 py-2 rounded-lg text-xs font-medium bg-accent-muted text-accent border border-accent-border"
          >
            Retry
          </button>
        </div>
      ) : allArticles.length === 0 ? (
        <div className="text-center py-20 rounded-xl bg-bg-card border border-border">
          <p className="text-sm font-medium mb-2 text-text-primary">No articles yet</p>
          <p className="text-xs text-(--color-text-muted)">
            Click &quot;Scrape Now&quot; to fetch articles from Inshorts, RSS, and NewsAPI.
          </p>
        </div>
      ) : (
        <>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5 stagger-children">
            {allArticles.map((article, i) => (
              <ArticleCard key={article.id} article={article} index={i} />
            ))}
          </div>

          <div className="mt-10 flex flex-col items-center gap-3">
            <p className="text-xs text-(--color-text-muted)">
              Showing {allArticles.length} of {totalCount} articles
            </p>
            {hasNextPage && (
              <button
                onClick={() => fetchNextPage()}
                disabled={isFetchingNextPage}
                className="px-6 py-2.5 rounded-lg text-xs font-medium transition-colors duration-150
                           bg-bg-card text-accent
                           border border-border hover:border-accent-border
                           disabled:opacity-50"
              >
                {isFetchingNextPage ? (
                  <span className="flex items-center gap-2">
                    <Loader2 className="w-3.5 h-3.5 animate-spin" /> Loading...
                  </span>
                ) : (
                  "Show More"
                )}
              </button>
            )}
          </div>
        </>
      )}
    </div>
  );
}
