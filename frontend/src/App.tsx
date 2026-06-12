import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { ConfigProvider, App as AntdApp } from 'antd';
import zhCN from 'antd/locale/zh_CN';
import AppLayout from '@/components/AppLayout';
import SubmitApplication from '@/pages/staff/SubmitApplication';
import TrackApplications from '@/pages/staff/TrackApplications';
import ApplicationDetail from '@/pages/staff/ApplicationDetail';
import Dashboard from '@/pages/admin/Dashboard';
import WorkerMonitor from '@/pages/admin/WorkerMonitor';

export default function App() {
  return (
    <ConfigProvider locale={zhCN}>
      <AntdApp>
        <BrowserRouter>
          <Routes>
            <Route path="/" element={<AppLayout />}>
              <Route index element={<Navigate to="/staff/submit" replace />} />
              <Route path="staff/submit" element={<SubmitApplication />} />
              <Route path="staff/track" element={<TrackApplications />} />
              <Route path="staff/detail/:id" element={<ApplicationDetail />} />
              <Route path="admin/dashboard" element={<Dashboard />} />
              <Route path="admin/workers" element={<WorkerMonitor />} />
            </Route>
          </Routes>
        </BrowserRouter>
      </AntdApp>
    </ConfigProvider>
  );
}
