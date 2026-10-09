import { BrowserRouter, Navigate, Routes, Route } from 'react-router-dom';
import DashboardPage from './pages/DashboardPage';
import TraceabilityPage from './pages/TraceabilityPage';
import HolidayCalendarPage from './pages/HolidayCalendarPage';
import UnitAreaPage from './pages/UnitAreaPage';

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<DashboardPage />} />
        <Route path="/sla4" element={<Navigate to="/" replace />} />
        <Route path="/units" element={<UnitAreaPage />} />
        <Route path="/traceability" element={<TraceabilityPage />} />
        <Route path="/holidays" element={<HolidayCalendarPage />} />
      </Routes>
    </BrowserRouter>
  );
}
