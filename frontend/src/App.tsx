import { useEffect, useMemo, useRef, useState } from "react";
import { fetchCourses, type Course } from "./api";
import ChatPanel from "./components/ChatPanel";
import CourseCard from "./components/CourseCard";
import { LeafMark, SearchIcon } from "./components/icons";

export default function App() {
  const [courses, setCourses] = useState<Course[]>([]);
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const debounce = useRef<number | undefined>(undefined);

  useEffect(() => {
    const controller = new AbortController();

    // Debounce so typing doesn't fire a request per keystroke.
    window.clearTimeout(debounce.current);
    debounce.current = window.setTimeout(() => {
      setLoading(true);
      fetchCourses(query, controller.signal)
        .then((res) => {
          setCourses(res.courses);
          setError(null);
        })
        .catch((err: unknown) => {
          if (err instanceof DOMException && err.name === "AbortError") return;
          setError(
            err instanceof Error ? err.message : "Could not load courses",
          );
        })
        .finally(() => setLoading(false));
    }, 220);

    return () => {
      controller.abort();
      window.clearTimeout(debounce.current);
    };
  }, [query]);

  const countLabel = useMemo(() => {
    if (loading) return "Loading…";
    if (error) return "";
    const n = courses.length;
    return `${n} course${n === 1 ? "" : "s"}${query.trim() ? " matched" : ""}`;
  }, [courses.length, loading, error, query]);

  return (
    <div className="app">
      <header className="masthead">
        <span className="mark">
          <LeafMark />
        </span>
        <div>
          <h1>Yale SOM Course Explorer</h1>
          <p className="tagline">
            Browse the catalog, then ask the{" "}
            <span className="gold">course assistant</span> anything it can
            answer from the data.
          </p>
        </div>
      </header>

      <div className="layout">
        <main>
          <div className="toolbar">
            <div className="search">
              <SearchIcon />
              <input
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Search by title, number, professor, topic…"
                aria-label="Search courses"
              />
            </div>
            <span className="result-count">
              {countLabel && <strong>{countLabel}</strong>}
            </span>
          </div>

          {error && (
            <div className="notice">
              <strong>Can't reach the backend.</strong> Start it with{" "}
              <code>uvicorn main:app --port 8000</code> from{" "}
              <code>backend/</code>. ({error})
            </div>
          )}

          {loading && !error && (
            <div className="grid">
              {Array.from({ length: 6 }, (_, i) => (
                <div key={i} className="skeleton" />
              ))}
            </div>
          )}

          {!loading && !error && courses.length === 0 && (
            <div className="notice">
              No courses match <strong>{query}</strong>. Try a broader search.
            </div>
          )}

          {!loading && !error && courses.length > 0 && (
            <div className="grid">
              {courses.map((c, i) => (
                <CourseCard key={`${c["Course ID"]}-${c.Section}-${i}`} course={c} />
              ))}
            </div>
          )}
        </main>

        <ChatPanel />
      </div>
    </div>
  );
}
