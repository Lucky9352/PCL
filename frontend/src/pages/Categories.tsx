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
      <h1 className="text-2xl font-bold mb-1 text-text-primary">Categories</h1>
      <p className="text-sm mb-7 text-text-secondary">Browse articles by category</p>

      {isLoading ? (
        <div className="flex justify-center py-20">
          <Loader2 className="w-6 h-6 animate-spin text-accent" />
        </div>
      ) : (
        <>
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3 mb-8">
            {categories?.map((cat) => (
              <button
                key={cat.name}
                onClick={() => setSelectedCategory(selectedCategory === cat.name ? null : cat.name)}
                className={`rounded-lg p-4 text-center transition-all duration-150 border ${
                  selectedCategory === cat.name
                    ? "bg-accent-muted border-accent-border"
                    : "bg-bg-card border-border hover:border-border-hover"
                }`}
              >
                <CategoryBadge category={cat.name} />
                <p className="mt-2.5 text-xl font-bold tabular-nums text-text-primary">
                  {cat.count}
                </p>
                <p className="text-[10px] text-(--color-text-muted)">articles</p>
              </button>
            ))}
          </div>

          {selectedCategory && (
            <div>
              <h2 className="text-lg font-bold mb-4 capitalize text-text-primary">
                {selectedCategory} articles
              </h2>
              {loadingArticles ? (
                <div className="flex justify-center py-10">
                  <Loader2 className="w-5 h-5 animate-spin text-accent" />
                </div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5 stagger-children">
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
