import { Routes, Route } from "react-router-dom";
import Navbar from "./components/Navbar";
import Footer from "./components/Footer";
import Home from "./pages/Home";
import ArticleDetail from "./pages/ArticleDetail";
import Categories from "./pages/Categories";
import Dashboard from "./pages/Dashboard";
import Stories from "./pages/Stories";
import StoryDetail from "./pages/StoryDetail";
import Methodology from "./pages/Methodology";

function App() {
  return (
    <div className="min-h-screen flex flex-col" style={{ background: "var(--color-bg-primary)" }}>
      <Navbar />
      <main className="flex-1 max-w-7xl mx-auto w-full px-4 sm:px-6 lg:px-8 pt-20 pb-12">
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/article/:id" element={<ArticleDetail />} />
          <Route path="/categories" element={<Categories />} />
          <Route path="/stories" element={<Stories />} />
          <Route path="/story/:id" element={<StoryDetail />} />
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/methodology" element={<Methodology />} />
        </Routes>
      </main>
      <Footer />
    </div>
  );
}

export default App;
