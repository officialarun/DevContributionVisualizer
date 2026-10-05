import { Navigate, Route, Routes } from 'react-router-dom'
import Shell from './components/layout/Shell'
import RepoLayout from './components/layout/RepoLayout'
import Home from './pages/Home'
import Dashboard from './pages/Dashboard'
import Developers from './pages/Developers'
import DeveloperDetail from './pages/DeveloperDetail'
import Files from './pages/Files'
import Commits from './pages/Commits'

export default function App() {
  return (
    <Routes>
      <Route element={<Shell />}>
        <Route index element={<Home />} />
        <Route path="r/:id" element={<RepoLayout />}>
          <Route index element={<Dashboard />} />
          <Route path="developers" element={<Developers />} />
          <Route path="developers/:dev" element={<DeveloperDetail />} />
          <Route path="files" element={<Files />} />
          <Route path="commits" element={<Commits />} />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  )
}
