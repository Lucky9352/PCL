import { Routes, Route } from "react-router-dom";
import Navbar from "./components/Navbar";
import Home from "./pages/Home";
import ArticleDetail from "./pages/ArticleDetail";
import Categories from "./pages/Categories";
import Dashboard from "./pages/Dashboard";

function App() {
  return (
    <div className="min-h-screen" style={{ background: "var(--color-bg-primary)" }}>
      <Navbar />
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-20 pb-12">
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/article/:id" element={<ArticleDetail />} />
          <Route path="/categories" element={<Categories />} />
          <Route path="/dashboard" element={<Dashboard />} />
        </Routes>
      </main>
    </div>
  );
}

export default App;
