import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { Card, Input, Button, ErrorMessage, Select } from '../components';
import { Compass, Key, UserPlus, LogIn } from 'lucide-react';
import { UserRole } from '../types';

export const Login: React.FC = () => {
  const { login, register, error, clearError, isLoading } = useAuth();
  const navigate = useNavigate();

  const [isRegistering, setIsRegistering] = useState(false);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [fullName, setFullName] = useState('');
  const [phoneNumber, setPhoneNumber] = useState('');
  const [nationality, setNationality] = useState('');
  const [role, setRole] = useState<UserRole>('TOURIST');
  const [localError, setLocalError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLocalError(null);
    clearError();

    try {
      if (isRegistering) {
        if (!email || !password || !fullName) {
          setLocalError('Please fill in all required fields (Name, Email, Password).');
          return;
        }
        await register({
          email,
          password,
          full_name: fullName,
          phone_number: phoneNumber || undefined,
          nationality: nationality || undefined,
          role,
        });
      } else {
        if (!email || !password) {
          setLocalError('Please enter both email and password.');
          return;
        }
        await login({ email, password });
      }
      navigate('/');
    } catch (err: any) {
      // Error is handled in context
    }
  };

  return (
    <div style={{ maxWidth: 460, margin: '60px auto 0 auto' }}>
      <div style={{ textAlign: 'center', marginBottom: 28 }}>
        <div
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            justifyContent: 'center',
            width: 48,
            height: 48,
            borderRadius: '12px',
            backgroundColor: 'var(--bg-card)',
            border: '1px solid var(--border-main)',
            marginBottom: 12,
          }}
        >
          <Compass size={24} color="var(--accent-primary)" />
        </div>
        <h2 style={{ fontSize: '20px', fontWeight: 700, color: 'var(--text-primary)' }}>
          {isRegistering ? 'Create Research / Test Account' : 'Tourist Safety Backend Sign In'}
        </h2>
        <p style={{ fontSize: '13px', color: 'var(--text-secondary)', marginTop: 4 }}>
          Connect directly to FastAPI authentication endpoints
        </p>
      </div>

      <Card>
        <ErrorMessage error={localError || error} onDismiss={() => { setLocalError(null); clearError(); }} />

        <form onSubmit={handleSubmit}>
          {isRegistering && (
            <>
              <Input
                label="Full Name *"
                type="text"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                placeholder="e.g. Anil Kumar"
                required
              />
              <div className="form-grid-2">
                <Input
                  label="Phone Number"
                  type="tel"
                  value={phoneNumber}
                  onChange={(e) => setPhoneNumber(e.target.value)}
                  placeholder="+919876543210"
                />
                <Input
                  label="Nationality"
                  type="text"
                  value={nationality}
                  onChange={(e) => setNationality(e.target.value)}
                  placeholder="e.g. Indian"
                />
              </div>
              <Select
                label="System Role"
                value={role}
                onChange={(e) => setRole(e.target.value as UserRole)}
                options={[
                  { value: 'TOURIST', label: 'Tourist' },
                  { value: 'RESPONDER', label: 'Emergency Responder' },
                  { value: 'ADMIN', label: 'System Admin' },
                ]}
              />
            </>
          )}

          <Input
            label="Email Address *"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="name@example.com"
            required
          />

          <Input
            label="Password *"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="••••••••"
            helperText={isRegistering ? 'Minimum 8 characters' : undefined}
            required
          />

          <Button
            type="submit"
            variant="primary"
            isLoading={isLoading}
            style={{ width: '100%', marginTop: 8 }}
            icon={isRegistering ? <UserPlus size={16} /> : <LogIn size={16} />}
          >
            {isRegistering ? 'Register & Sign In' : 'Sign In'}
          </Button>
        </form>

        <div
          style={{
            marginTop: 20,
            paddingTop: 16,
            borderTop: '1px solid var(--border-subtle)',
            textAlign: 'center',
            fontSize: '13px',
            color: 'var(--text-secondary)',
          }}
        >
          {isRegistering ? (
            <span>
              Already have an account?{' '}
              <button
                type="button"
                onClick={() => { setIsRegistering(false); clearError(); }}
                style={{ background: 'none', border: 'none', color: 'var(--accent-primary)', fontWeight: 600, cursor: 'pointer', textDecoration: 'underline' }}
              >
                Sign In
              </button>
            </span>
          ) : (
            <span>
              Need a test account?{' '}
              <button
                type="button"
                onClick={() => { setIsRegistering(true); clearError(); }}
                style={{ background: 'none', border: 'none', color: 'var(--accent-primary)', fontWeight: 600, cursor: 'pointer', textDecoration: 'underline' }}
              >
                Register New User
              </button>
            </span>
          )}
        </div>
      </Card>

      <div
        style={{
          marginTop: 16,
          padding: '12px 16px',
          backgroundColor: 'var(--bg-secondary)',
          border: '1px solid var(--border-subtle)',
          borderRadius: 'var(--radius-sm)',
          fontSize: '12px',
          color: 'var(--text-secondary)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontWeight: 600, color: 'var(--text-primary)', marginBottom: 4 }}>
          <Key size={14} />
          <span>Research Testing Information</span>
        </div>
        Calls <code>POST /api/v1/auth/login</code> and <code>POST /api/v1/auth/register</code>. JWT tokens are stored for session requests.
      </div>
    </div>
  );
};
