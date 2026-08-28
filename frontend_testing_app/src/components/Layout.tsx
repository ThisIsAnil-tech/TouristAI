import React from 'react';
import { NavLink, Outlet, useNavigate } from 'react-router-dom';
import {
  LayoutDashboard,
  MapPin,
  ShieldAlert,
  Mic,
  AlertOctagon,
  Radio,
  Share2,
  Cpu,
  FlaskConical,
  Activity,
  User,
  LogOut,
  Compass,
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { StatusBadge } from './StatusBadge';

export const Layout: React.FC = () => {
  const { user, logout, isAuthenticated } = useAuth();
  const navigate = useNavigate();

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  const navItems = [
    { section: 'Core Platform' },
    { to: '/', label: 'Overview', icon: <LayoutDashboard size={18} /> },
    { to: '/gps', label: 'GPS Safety', icon: <MapPin size={18} /> },
    { to: '/risk', label: 'Environmental Risk', icon: <ShieldAlert size={18} /> },
    { to: '/audio', label: 'Audio Detection', icon: <Mic size={18} /> },
    { to: '/sos', label: 'Emergency / SOS', icon: <AlertOctagon size={18} /> },
    { section: 'Network & Security' },
    { to: '/communication', label: 'Communication', icon: <Radio size={18} /> },
    { to: '/mesh', label: 'Mesh Network', icon: <Share2 size={18} /> },
    { to: '/blockchain', label: 'Blockchain Identity', icon: <Cpu size={18} /> },
    { section: 'Research & System' },
    { to: '/experiments', label: 'Experiments', icon: <FlaskConical size={18} /> },
    { to: '/system', label: 'System Status', icon: <Activity size={18} /> },
    { to: '/profile', label: 'User Profile', icon: <User size={18} /> },
  ];

  return (
    <div className="app-container">
      {/* Left Sidebar */}
      <aside className="app-sidebar">
        <div className="sidebar-header">
          <div className="sidebar-title">
            <Compass size={20} />
            <span>Tourist Safety</span>
          </div>
          <div className="sidebar-subtitle">Research & Testing Platform</div>
        </div>

        <nav className="sidebar-nav">
          {navItems.map((item, idx) => {
            if (item.section) {
              return (
                <div key={idx} className="nav-section-title">
                  {item.section}
                </div>
              );
            }
            return (
              <NavLink
                key={item.to}
                to={item.to!}
                className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
                end={item.to === '/'}
              >
                {item.icon}
                <span>{item.label}</span>
              </NavLink>
            );
          })}
        </nav>

        <div className="sidebar-footer">
          {isAuthenticated && user ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <div style={{ minWidth: 0 }}>
                  <div
                    style={{
                      fontSize: '13px',
                      fontWeight: 600,
                      color: 'var(--text-primary)',
                      whiteSpace: 'nowrap',
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                    }}
                  >
                    {user.full_name}
                  </div>
                  <div
                    style={{
                      fontSize: '11px',
                      color: 'var(--text-secondary)',
                      whiteSpace: 'nowrap',
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                    }}
                  >
                    {user.email}
                  </div>
                </div>
                <StatusBadge status={user.role} size="sm" />
              </div>
              <button
                onClick={handleLogout}
                className="btn btn-sm"
                style={{ width: '100%', justifyContent: 'center' }}
              >
                <LogOut size={14} />
                <span>Logout</span>
              </button>
            </div>
          ) : (
            <button
              onClick={() => navigate('/login')}
              className="btn btn-sm btn-primary"
              style={{ width: '100%', justifyContent: 'center' }}
            >
              <span>Sign In</span>
            </button>
          )}
        </div>
      </aside>

      {/* Main Area */}
      <main className="app-main">
        <header className="app-topbar">
          <div className="topbar-breadcrumbs">
            <span>Tourist AI Safety System</span>
            <span>/</span>
            <strong>Testing Console</strong>
          </div>
          <div className="topbar-actions">
            <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
              Backend: {import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'}
            </span>
          </div>
        </header>

        <div className="page-content">
          <Outlet />
        </div>
      </main>
    </div>
  );
};
