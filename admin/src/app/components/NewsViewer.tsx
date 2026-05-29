"use client";

import { useEffect, useState } from "react";

type Source = {
  id: string;
  label: string;
};

type NewsItem = {
  title: string;
  link: string;
  published: string;
  content: string;
};

type NewsResult = {
  sourceId: string;
  label: string;
  items: NewsItem[];
  error?: string;
};

export default function NewsViewer() {
  const [sources, setSources] = useState<Source[]>([]);
  const [results, setResults] = useState<NewsResult[]>([]);
  const [sourceId, setSourceId] = useState<string>("all");
  const [limit, setLimit] = useState<number>(5);
  const [loading, setLoading] = useState(false);

  const loadSources = async () => {
    const response = await fetch("/api/sources", { cache: "no-store" });
    const data = await response.json();
    setSources(data.sources ?? []);
  };

  const loadNews = async (selectedId: string, selectedLimit: number) => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (selectedId !== "all") {
        params.set("sourceId", selectedId);
      }
      params.set("limit", String(selectedLimit));

      const response = await fetch(`/api/news?${params.toString()}`, {
        cache: "no-store",
      });
      const data = await response.json();
      setResults(data.results ?? []);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadSources();
  }, []);

  useEffect(() => {
    void loadNews(sourceId, limit);
  }, [sourceId, limit]);

  return (
    <section className="card">
      <h2>Новости</h2>
      <div className="filters">
        <label>
          Источник
          <select
            value={sourceId}
            onChange={(event) => setSourceId(event.target.value)}
          >
            <option value="all">Все</option>
            {sources.map((source) => (
              <option key={source.id} value={source.id}>
                {source.label}
              </option>
            ))}
          </select>
        </label>
        <label>
          Лимит
          <input
            type="number"
            min={1}
            max={20}
            value={limit}
            onChange={(event) => setLimit(Number(event.target.value))}
          />
        </label>
        <button onClick={() => loadNews(sourceId, limit)}>Обновить</button>
      </div>

      {loading ? <p className="muted">Загрузка...</p> : null}

      <div className="news-grid">
        {results.map((result) => (
          <article key={result.sourceId} className="news-card">
            <h3>{result.label}</h3>
            {result.error ? (
              <p className="notice">{result.error}</p>
            ) : result.items.length === 0 ? (
              <p className="muted">Нет новых новостей.</p>
            ) : (
              <ul>
                {result.items.map((item, index) => (
                  <li key={`${result.sourceId}-${index}`}>
                    <a href={item.link} target="_blank" rel="noreferrer">
                      {item.title || item.link}
                    </a>
                    {item.published ? (
                      <span className="meta">{item.published}</span>
                    ) : null}
                    {item.content ? (
                      <p className="snippet">{item.content}</p>
                    ) : null}
                  </li>
                ))}
              </ul>
            )}
          </article>
        ))}
      </div>
    </section>
  );
}
