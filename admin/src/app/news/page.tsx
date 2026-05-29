import NewsViewer from "@/app/components/NewsViewer";

export default function NewsPage() {
  return (
    <div className="page">
      <header className="page-header">
        <h1>Новости и ссылки</h1>
        <p className="muted">
          Новости загружаются при просмотре, без хранения в базе.
        </p>
      </header>
      <NewsViewer />
    </div>
  );
}
