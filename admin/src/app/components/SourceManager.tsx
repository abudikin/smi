"use client";

import { useEffect, useMemo, useState } from "react";

type SourceType = "rss" | "telegram";

type Source = {
  id: string;
  label: string;
  type: SourceType;
  rssUrl: string | null;
  channel: string | null;
};

type FormState = {
  label: string;
  type: SourceType;
  rssUrl: string;
  channel: string;
};

const emptyForm: FormState = {
  label: "",
  type: "rss",
  rssUrl: "",
  channel: "",
};

export default function SourceManager() {
  const [sources, setSources] = useState<Source[]>([]);
  const [form, setForm] = useState<FormState>(emptyForm);
  const [message, setMessage] = useState<string>("");
  const [loading, setLoading] = useState(false);

  const canSubmit = useMemo(() => {
    if (!form.label.trim()) return false;
    if (form.type === "rss") return Boolean(form.rssUrl.trim());
    return Boolean(form.channel.trim() || form.rssUrl.trim());
  }, [form]);

  const loadSources = async () => {
    setLoading(true);
    try {
      const response = await fetch("/api/sources", { cache: "no-store" });
      const data = await response.json();
      setSources(data.sources ?? []);
    } catch (error) {
      setMessage("Не удалось загрузить источники.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadSources();
  }, []);

  const handleCreate = async () => {
    if (!canSubmit) return;
    setMessage("");
    try {
      const response = await fetch("/api/sources", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(form),
      });
      const data = await response.json();
      if (!response.ok) {
        setMessage(data.error ?? "Ошибка создания.");
        return;
      }
      setSources((prev) => [data.source, ...prev]);
      setForm(emptyForm);
    } catch (error) {
      setMessage("Ошибка создания источника.");
    }
  };

  const handleUpdate = async (source: Source) => {
    setMessage("");
    try {
      const response = await fetch(`/api/sources/${source.id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          label: source.label,
          type: source.type,
          rssUrl: source.rssUrl ?? "",
          channel: source.channel ?? "",
        }),
      });
      const data = await response.json();
      if (!response.ok) {
        setMessage(data.error ?? "Ошибка обновления.");
        return;
      }
      setSources((prev) =>
        prev.map((item) => (item.id === source.id ? data.source : item))
      );
    } catch (error) {
      setMessage("Ошибка обновления источника.");
    }
  };

  const handleDelete = async (id: string) => {
    if (!window.confirm("Удалить источник?")) return;
    setMessage("");
    try {
      const response = await fetch(`/api/sources/${id}`, { method: "DELETE" });
      if (!response.ok) {
        setMessage("Ошибка удаления.");
        return;
      }
      setSources((prev) => prev.filter((item) => item.id !== id));
    } catch (error) {
      setMessage("Ошибка удаления источника.");
    }
  };

  const updateSource = (id: string, patch: Partial<Source>) => {
    setSources((prev) =>
      prev.map((item) => (item.id === id ? { ...item, ...patch } : item))
    );
  };

  return (
    <section className="card">
      <h2>Источники</h2>
      <p className="muted">
        Для Telegram укажите channel без @ или прямой RSS URL.
      </p>

      <div className="form-grid">
        <input
          placeholder="Название"
          value={form.label}
          onChange={(event) => setForm({ ...form, label: event.target.value })}
        />
        <select
          value={form.type}
          onChange={(event) =>
            setForm({ ...form, type: event.target.value as SourceType })
          }
        >
          <option value="rss">rss</option>
          <option value="telegram">telegram</option>
        </select>
        <input
          placeholder="RSS URL"
          value={form.rssUrl}
          onChange={(event) => setForm({ ...form, rssUrl: event.target.value })}
        />
        <input
          placeholder="Telegram channel"
          value={form.channel}
          onChange={(event) => setForm({ ...form, channel: event.target.value })}
        />
        <button onClick={handleCreate} disabled={!canSubmit}>
          Добавить источник
        </button>
      </div>

      {message ? <p className="notice">{message}</p> : null}
      {loading ? <p className="muted">Загрузка...</p> : null}

      <div className="table">
        <div className="row header">
          <span>Название</span>
          <span>Тип</span>
          <span>RSS URL</span>
          <span>Channel</span>
          <span>Действия</span>
        </div>
        {sources.map((source) => (
          <div className="row" key={source.id}>
            <input
              value={source.label}
              onChange={(event) =>
                updateSource(source.id, { label: event.target.value })
              }
            />
            <select
              value={source.type}
              onChange={(event) =>
                updateSource(source.id, {
                  type: event.target.value as SourceType,
                })
              }
            >
              <option value="rss">rss</option>
              <option value="telegram">telegram</option>
            </select>
            <input
              value={source.rssUrl ?? ""}
              onChange={(event) =>
                updateSource(source.id, { rssUrl: event.target.value })
              }
            />
            <input
              value={source.channel ?? ""}
              onChange={(event) =>
                updateSource(source.id, { channel: event.target.value })
              }
            />
            <div className="actions">
              <button onClick={() => handleUpdate(source)}>Сохранить</button>
              <button
                className="danger"
                onClick={() => handleDelete(source.id)}
              >
                Удалить
              </button>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
