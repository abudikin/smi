import SourceManager from "@/app/components/SourceManager";

export default function Home() {
  return (
    <div className="page">
      <header className="page-header">
        <h1>Админка источников</h1>
        <p className="muted">
          Добавляйте RSS/Telegram источники и управляйте списком.
        </p>
      </header>
      <SourceManager />
    </div>
  );
}
