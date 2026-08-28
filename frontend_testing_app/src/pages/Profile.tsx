import React, { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import {
  PageHeader,
  Card,
  Input,
  Button,
  StatusBadge,
  ErrorMessage,
  MessageBanner,
} from '../components';
import { usersApi } from '../api/users';
import { getErrorMessage } from '../api/client';
import { User, Save } from 'lucide-react';

export const ProfilePage: React.FC = () => {
  const { user, refreshProfile, isAuthenticated } = useAuth();

  const [fullName, setFullName] = useState<string>(user?.full_name || '');
  const [phoneNumber, setPhoneNumber] = useState<string>(user?.phone_number || '');
  const [nationality, setNationality] = useState<string>(user?.nationality || '');

  const [isUpdating, setIsUpdating] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  // Sync state when user updates
  React.useEffect(() => {
    if (user) {
      setFullName(user.full_name || '');
      setPhoneNumber(user.phone_number || '');
      setNationality(user.nationality || '');
    }
  }, [user]);

  const handleUpdateProfile = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsUpdating(true);
    setError(null);
    setSuccessMsg(null);
    try {
      await usersApi.updateMyProfile({
        full_name: fullName,
        phone_number: phoneNumber || undefined,
        nationality: nationality || undefined,
      });
      await refreshProfile();
      setSuccessMsg('Profile updated successfully on backend database.');
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setIsUpdating(false);
    }
  };

  if (!isAuthenticated || !user) {
    return (
      <div style={{ maxWidth: 500, margin: '40px auto', textAlign: 'center' }}>
        <Card>
          <p style={{ color: 'var(--text-secondary)', marginBottom: 12 }}>
            You are not signed in. Please sign in to access your user profile.
          </p>
          <Button variant="primary" onClick={() => (window.location.href = '/login')}>
            Go to Login
          </Button>
        </Card>
      </div>
    );
  }

  return (
    <div>
      <PageHeader
        title="Tourist Profile & Account"
        subtitle="Manage user credentials and inspect on-chain registration state"
      />

      <ErrorMessage error={error} onDismiss={() => setError(null)} />
      {successMsg && <MessageBanner type="success" message={successMsg} onDismiss={() => setSuccessMsg(null)} />}

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1.2fr', gap: 20 }}>
        {/* Profile Card */}
        <Card title="Account Metadata" subtitle="Backend identity record" icon={<User size={16} />}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', paddingBottom: 8, borderBottom: '1px solid var(--border-subtle)' }}>
              <span style={{ color: 'var(--text-secondary)' }}>User ID:</span>
              <span className="mono" style={{ fontSize: '11px' }}>{user.id}</span>
            </div>

            <div style={{ display: 'flex', justifyContent: 'space-between', paddingBottom: 8, borderBottom: '1px solid var(--border-subtle)' }}>
              <span style={{ color: 'var(--text-secondary)' }}>Email Address:</span>
              <span className="mono">{user.email}</span>
            </div>

            <div style={{ display: 'flex', justifyContent: 'space-between', paddingBottom: 8, borderBottom: '1px solid var(--border-subtle)' }}>
              <span style={{ color: 'var(--text-secondary)' }}>System Role:</span>
              <StatusBadge status={user.role} size="sm" />
            </div>

            <div style={{ display: 'flex', justifyContent: 'space-between', paddingBottom: 8, borderBottom: '1px solid var(--border-subtle)' }}>
              <span style={{ color: 'var(--text-secondary)' }}>Blockchain Identity:</span>
              <StatusBadge
                status={user.blockchain_registered ? 'ACTIVE' : 'NOT_RUN'}
                label={user.blockchain_registered ? 'Registered On-Chain' : 'Not Registered'}
                size="sm"
              />
            </div>

            <div style={{ display: 'flex', justifyContent: 'space-between', paddingBottom: 8, borderBottom: '1px solid var(--border-subtle)' }}>
              <span style={{ color: 'var(--text-secondary)' }}>Account Active:</span>
              <StatusBadge status={user.is_active} size="sm" />
            </div>

            <div style={{ display: 'flex', justifyContent: 'space-between', paddingBottom: 8, borderBottom: '1px solid var(--border-subtle)' }}>
              <span style={{ color: 'var(--text-secondary)' }}>Last Location:</span>
              <span className="mono">
                {user.last_latitude && user.last_longitude
                  ? `${user.last_latitude.toFixed(4)}, ${user.last_longitude.toFixed(4)}`
                  : 'Not recorded'}
              </span>
            </div>

            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ color: 'var(--text-secondary)' }}>Registered On:</span>
              <span>{new Date(user.created_at).toLocaleDateString()}</span>
            </div>
          </div>
        </Card>

        {/* Edit Form */}
        <Card title="Edit User Information" subtitle="PATCH /api/v1/users/me">
          <form onSubmit={handleUpdateProfile}>
            <Input
              label="Full Name *"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              placeholder="Full Name"
              required
            />

            <Input
              label="Phone Number"
              type="tel"
              value={phoneNumber}
              onChange={(e) => setPhoneNumber(e.target.value)}
              placeholder="+919876543210"
            />

            <Input
              label="Nationality"
              value={nationality}
              onChange={(e) => setNationality(e.target.value)}
              placeholder="e.g. Indian"
            />

            <Button
              type="submit"
              variant="primary"
              isLoading={isUpdating}
              icon={<Save size={15} />}
              style={{ width: '100%', marginTop: 8 }}
            >
              Save Profile Changes
            </Button>
          </form>
        </Card>
      </div>
    </div>
  );
};
