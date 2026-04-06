import { useQuery } from "@tanstack/react-query";
import { fetchCategories, fetchArticles } from "@/api/client";
import CategoryBadge from "@/components/CategoryBadge";
import ArticleCard from "@/components/ArticleCard";
import { useState } from "react";
import { Loader2 } from "lucide-react";

export default function Categories() {
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);

  const { data: categories, isLoading } = useQuery({
    queryKey: ["categories"],
    queryFn: fetchCategories,
  });

  const { data: articles, isLoading: loadingArticles } = useQuery({
    queryKey: ["articles", "category", selectedCategory],
    queryFn: () => fetchArticles({ page_size: 20, category: selectedCategory || undefined }),
    enabled: !!selectedCategory,
  });

  return (
    <div className="animate-fade-in">
      <h1 className="text-3xl font-bold mb-2" style={{ color: "var(--color-text-primary)" }}>
        Categories
      </h1>
      <p className="mb-8" style={{ color: "var(--color-text-secondary)" }}>
        Browse articles by category
      </p>

      {isLoading ? (
        <div className="flex justify-center py-20">
          <Loader2 className="w-8 h-8 animate-spin" style={{ color: "var(--color-accent)" }} />
        </div>
      ) : (
        <>
          {/* Category grid */}
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3 mb-10">
            {categories?.map((cat) => (
              <button
                key={cat.name}
                onClick={() => setSelectedCategory(selectedCategory === cat.name ? null : cat.name)}
                className="rounded-xl p-4 text-center transition-all duration-200 hover:-translate-y-1"
                style={{
                  background:
                    selectedCategory === cat.name
                      ? "rgba(99, 102, 241, 0.15)"
                      : "var(--color-bg-card)",
                  border:
                    selectedCategory === cat.name
                      ? "1px solid rgba(99, 102, 241, 0.3)"
                      : "1px solid var(--color-border)",
                  boxShadow: "var(--shadow-card)",
                }}
              >
                <CategoryBadge category={cat.name} />
                <p
                  className="mt-3 text-2xl font-bold"
                  style={{ color: "var(--color-text-primary)" }}
                >
                  {cat.count}
                </p>
                <p className="text-xs" style={{ color: "var(--color-text-muted)" }}>
                  articles
                </p>
              </button>
            ))}
          </div>

          {/* Filtered articles */}
          {selectedCategory && (
            <div>
              <h2
                className="text-xl font-bold mb-4 capitalize"
                style={{ color: "var(--color-text-primary)" }}
              >
                {selectedCategory} articles
              </h2>
              {loadingArticles ? (
                <div className="flex justify-center py-10">
                  <Loader2
                    className="w-6 h-6 animate-spin"
                    style={{ color: "var(--color-accent)" }}
                  />
                </div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 stagger-children">
                  {articles?.data.map((article, i) => (
                    <ArticleCard key={article.id} article={article} index={i} />
                  ))}
                </div>
              )}
            </div>
          )}
        </>
      )}
    </div>
  );
}
