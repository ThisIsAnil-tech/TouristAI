import React, { useEffect, useState } from 'react';
import { useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import {
  PageHeader,
  Card,
  Input,
  Button,
  StatusBadge,
  ErrorMessage,
  DataTable,
  Column,
  LoadingState,
  Modal,
  MessageBanner,
} from '../components';
import { communicationApi } from '../api/communication';
import { CommAttemptResponse, ContactResponse } from '../types';
import { getErrorMessage } from '../api/client';
import {
  Radio,
  Send,
  RefreshCw,
  Plus,
  Trash2,
  Phone,
  Zap,
} from 'lucide-react';

export const CommunicationPage: React.FC = () => {
  const { isAuthenticated } = useAuth();
  const location = useLocation();

  // If passed from SOS page
  const initialSosId = (location.state as any)?.sosId || '';
  const [sosEventId, setSosEventId] = useState<string>(initialSosId);

  const [attempts, setAttempts] = useState<CommAttemptResponse[]>([]);
  const [contacts, setContacts] = useState<ContactResponse[]>([]);

  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [isSending, setIsSending] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [infoMessage, setInfoMessage] = useState<string | null>(null);

  // Add Contact Modal State
  const [isContactModalOpen, setIsContactModalOpen] = useState<boolean>(false);
  const [contactName, setContactName] = useState<string>('');
  const [contactRelationship, setContactRelationship] = useState<string>('Family');
  const [contactPhone, setContactPhone] = useState<string>('+919876543210');
  const [contactEmail, setContactEmail] = useState<string>('contact@example.com');
  const [isPrimary, setIsPrimary] = useState<boolean>(true);
  const [notifyOnSos, setNotifyOnSos] = useState<boolean>(true);

  const fetchContacts = async () => {
    if (!isAuthenticated) return;
    try {
      const res = await communicationApi.listContacts();
      setContacts(res);
    } catch (err) {
      console.warn('Failed to load contacts', err);
    }
  };

  const fetchAttempts = async () => {
    if (!sosEventId) return;
    setIsLoading(true);
    setError(null);
    try {
      const res = await communicationApi.getAttemptsForSos(sosEventId);
      setAttempts(res);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchContacts();
    if (initialSosId) {
      fetchAttempts();
    }
  }, [isAuthenticated, initialSosId]);

  const handleSendAlerts = async () => {
    if (!sosEventId) {
      setError('Please enter a valid SOS Event UUID to trigger communication pipeline.');
      return;
    }
    setIsSending(true);
    setError(null);
    setInfoMessage(null);
    try {
      const res = await communicationApi.sendEmergencyAlert(sosEventId);
      setInfoMessage(`Emergency alert dispatched to ${res.notified} contacts via fallback manager.`);
      await fetchAttempts();
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setIsSending(false);
    }
  };

  const handleRetryFailed = async () => {
    if (!sosEventId) return;
    setIsSending(true);
    setError(null);
    try {
      const res = await communicationApi.retryFailedAttempts(sosEventId);
      setInfoMessage(`Retrying ${res.retrying} failed communication attempts.`);
      await fetchAttempts();
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setIsSending(false);
    }
  };

  const handleAddContact = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await communicationApi.addContact({
        name: contactName,
        relationship: contactRelationship,
        phone_number: contactPhone,
        email: contactEmail || undefined,
        is_primary: isPrimary,
        notify_on_sos: notifyOnSos,
      });
      setIsContactModalOpen(false);
      await fetchContacts();
    } catch (err) {
      setError(getErrorMessage(err));
    }
  };

  const handleRemoveContact = async (id: string) => {
    try {
      await communicationApi.removeContact(id);
      await fetchContacts();
    } catch (err) {
      setError(getErrorMessage(err));
    }
  };

  const attemptColumns: Column<CommAttemptResponse>[] = [
    { header: 'Channel', accessor: (a) => <strong>{a.channel}</strong> },
    { header: 'Destination', accessor: (a) => <span className="mono">{a.destination}</span> },
    { header: 'Status', accessor: (a) => <StatusBadge status={a.status} size="sm" /> },
    { header: 'Latency (ms)', accessor: (a) => (a.latency_ms != null ? `${a.latency_ms.toFixed(1)} ms` : '—') },
    { header: 'Retries', accessor: (a) => <span className="mono">{a.retry_count}</span> },
    { header: 'Attempt At', accessor: (a) => new Date(a.attempt_at).toLocaleTimeString() },
    { header: 'Error / Note', accessor: (a) => a.error_message || 'OK' },
  ];

  const contactColumns: Column<ContactResponse>[] = [
    { header: 'Name', accessor: (c) => <strong>{c.name}</strong> },
    { header: 'Relationship', accessor: (c) => c.relationship || '—' },
    { header: 'Phone', accessor: (c) => <span className="mono">{c.phone_number}</span> },
    { header: 'Email', accessor: (c) => <span className="mono">{c.email || '—'}</span> },
    { header: 'Primary', accessor: (c) => (c.is_primary ? <StatusBadge status="ACTIVE" label="Primary" size="sm" /> : '—') },
    { header: 'Notify SOS', accessor: (c) => <StatusBadge status={c.notify_on_sos} size="sm" /> },
    {
      header: 'Actions',
      render: (c) => (
        <Button size="sm" variant="danger" onClick={() => handleRemoveContact(c.id)}>
          <Trash2 size={12} />
        </Button>
      ),
    },
  ];

  return (
    <div>
      <PageHeader
        title="Communication & Fallback Pipeline"
        subtitle="Tiered fallback transmission: Internet Alert → SMS Gateway → Mesh Multi-hop Relay"
      />

      <ErrorMessage error={error} onDismiss={() => setError(null)} />
      {infoMessage && <MessageBanner type="info" message={infoMessage} onDismiss={() => setInfoMessage(null)} />}

      {/* Workflow Visualizer */}
      <div className="workflow-steps">
        <span className="workflow-step active">
          <Zap size={14} /> Tier 1: Internet Alert (Fastest)
        </span>
        <span className="workflow-arrow">↓ fallback if failed</span>
        <span className="workflow-step active">
          <Phone size={14} /> Tier 2: SMS Gateway (Cellular)
        </span>
        <span className="workflow-arrow">↓ fallback if offline</span>
        <span className="workflow-step active">
          <Radio size={14} /> Tier 3: Mesh Network Routing
        </span>
      </div>

      {/* SOS Alert Dispatch Controller */}
      <Card title="Emergency Alert Dispatcher" subtitle="Trigger fallback communication workflow for an SOS event">
        <div style={{ display: 'flex', gap: 12, alignItems: 'flex-end', flexWrap: 'wrap' }}>
          <div style={{ flex: 1, minWidth: 280 }}>
            <Input
              label="Target SOS Event UUID *"
              value={sosEventId}
              onChange={(e) => setSosEventId(e.target.value)}
              placeholder="e.g. 123e4567-e89b-12d3-a456-426614174000"
            />
          </div>
          <div style={{ display: 'flex', gap: 8, marginBottom: 16 }}>
            <Button
              variant="primary"
              onClick={handleSendAlerts}
              isLoading={isSending}
              disabled={!sosEventId}
              icon={<Send size={14} />}
            >
              Trigger Full Fallback Pipeline
            </Button>
            <Button
              size="md"
              onClick={fetchAttempts}
              isLoading={isLoading}
              disabled={!sosEventId}
              icon={<RefreshCw size={14} />}
            >
              Fetch Attempts Log
            </Button>
            <Button
              size="md"
              onClick={handleRetryFailed}
              disabled={!sosEventId || isSending}
            >
              Retry Failed
            </Button>
          </div>
        </div>
      </Card>

      {/* Communication Attempts Table */}
      <div style={{ marginTop: 20 }}>
        <Card
          title="Transmission & Delivery Attempts"
          subtitle={`Attempts log for SOS Event: ${sosEventId || 'None selected'}`}
        >
          {isLoading ? (
            <LoadingState message="Fetching communication attempt logs..." />
          ) : (
            <DataTable
              columns={attemptColumns}
              data={attempts}
              keyExtractor={(a) => a.id}
              emptyMessage={
                sosEventId
                  ? 'No transmission attempts recorded for this SOS event yet.'
                  : 'Enter an SOS Event UUID above to query transmission attempts.'
              }
            />
          )}
        </Card>
      </div>

      {/* Emergency Contacts Management */}
      <div style={{ marginTop: 20 }}>
        <Card
          title="Configured Emergency Contacts"
          subtitle="Tourists can register emergency contacts to be notified on SOS triggers"
          action={
            <Button size="sm" icon={<Plus size={14} />} onClick={() => setIsContactModalOpen(true)}>
              Add Contact
            </Button>
          }
        >
          <DataTable
            columns={contactColumns}
            data={contacts}
            keyExtractor={(c) => c.id}
            emptyMessage="No emergency contacts registered for this account."
          />
        </Card>
      </div>

      {/* Add Contact Modal */}
      <Modal
        isOpen={isContactModalOpen}
        onClose={() => setIsContactModalOpen(false)}
        title="Add Emergency Contact"
      >
        <form onSubmit={handleAddContact}>
          <Input
            label="Full Name *"
            value={contactName}
            onChange={(e) => setContactName(e.target.value)}
            placeholder="e.g. Ramesh Kumar"
            required
          />
          <Input
            label="Relationship"
            value={contactRelationship}
            onChange={(e) => setContactRelationship(e.target.value)}
            placeholder="e.g. Spouse / Guide / Hotel Desk"
          />
          <Input
            label="Phone Number (E.164 format) *"
            type="tel"
            value={contactPhone}
            onChange={(e) => setContactPhone(e.target.value)}
            placeholder="+919876543210"
            required
          />
          <Input
            label="Email Address"
            type="email"
            value={contactEmail}
            onChange={(e) => setContactEmail(e.target.value)}
            placeholder="contact@example.com"
          />
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8, margin: '12px 0 16px 0' }}>
            <label style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: '13px', cursor: 'pointer' }}>
              <input
                type="checkbox"
                checked={isPrimary}
                onChange={(e) => setIsPrimary(e.target.checked)}
              />
              <span>Set as primary emergency contact</span>
            </label>
            <label style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: '13px', cursor: 'pointer' }}>
              <input
                type="checkbox"
                checked={notifyOnSos}
                onChange={(e) => setNotifyOnSos(e.target.checked)}
              />
              <span>Send automated alerts when SOS triggers</span>
            </label>
          </div>
          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8 }}>
            <Button type="button" onClick={() => setIsContactModalOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" variant="primary">
              Save Contact
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
};
