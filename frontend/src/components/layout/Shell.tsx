import { Link, Outlet } from 'react-router-dom'

export default function Shell() {
  return (
    <>
      <header className="header">
        <div className="header-inner">
          <Link to="/" className="brand">
            Contribution Visualizer
          </Link>
          <span className="muted tagline">Observe · Measure · Visualize · Explore</span>
        </div>
      </header>
      <main className="page">
        <Outlet />
        <p className="about">
          About these numbers: they count Git activity (commits, lines added and deleted, files touched) from the
          repository history, bucketed in UTC. Merge commits are not counted. Lines include generated, vendored and
          lock files. They describe activity, not productivity or the value of anyone’s work.
        </p>
      </main>
    </>
  )
}
