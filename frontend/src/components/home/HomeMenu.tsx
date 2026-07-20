import Link from "next/link";

export function HomeMenu() {
  return (
    <main className="home-menu-shell">
      <section className="home-menu">
        <h1>Sketchy</h1>
        <div className="home-menu-actions">
          <Link className="primary-button menu-button" href="/create">
            Create Room
          </Link>
          <Link className="secondary-button menu-button" href="/join">
            Join Room
          </Link>
        </div>
      </section>
    </main>
  );
}
