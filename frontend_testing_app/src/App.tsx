import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import { Layout } from './components/Layout';
import { Login } from './pages/Login';
import { Overview } from './pages/Overview';
import { GPSPage } from './pages/GPS';
import { RiskPage } from './pages/Risk';
import { AudioPage } from './pages/Audio';
import { SOSPage } from './pages/SOS';
import { CommunicationPage } from './pages/Communication';
import { MeshPage } from './pages/Mesh';
import { BlockchainPage } from './pages/Blockchain';
import { ExperimentsPage } from './pages/Experiments';
import { SystemStatusPage } from './pages/SystemStatus';
import { ProfilePage } from './pages/Profile';
import './styles/app.css';

export const App: React.FC = () => {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/" element={<Layout />}>
            <Route index element={<Overview />} />
            <Route path="gps" element={<GPSPage />} />
            <Route path="risk" element={<RiskPage />} />
            <Route path="audio" element={<AudioPage />} />
            <Route path="sos" element={<SOSPage />} />
            <Route path="communication" element={<CommunicationPage />} />
            <Route path="mesh" element={<MeshPage />} />
            <Route path="blockchain" element={<BlockchainPage />} />
            <Route path="experiments" element={<ExperimentsPage />} />
            <Route path="system" element={<SystemStatusPage />} />
            <Route path="profile" element={<ProfilePage />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
};

export default App;
