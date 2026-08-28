import React, { useEffect, useState } from 'react';
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
  MetricCard,
  MessageBanner,
} from '../components';
import { blockchainApi } from '../api/blockchain';
import { systemApi } from '../api/system';
import {
  BlockchainTxResponse,
  RegisterIdentityResponse,
  ResponderResponse,
} from '../types';
import { getErrorMessage } from '../api/client';
import {
  Cpu,
  ShieldCheck,
  Key,
  Lock,
  Unlock,
  RefreshCw,
  FileCheck,
  CheckCircle,
} from 'lucide-react';

export const BlockchainPage: React.FC = () => {
  const { user, refreshProfile } = useAuth();

  const [registerResult, setRegisterResult] = useState<RegisterIdentityResponse | null>(null);
  const [verifyStatus, setVerifyStatus] = useState<boolean | null>(null);
  const [transactions, setTransactions] = useState<BlockchainTxResponse[]>([]);
  const [responders, setResponders] = useState<ResponderResponse[]>([]);

  // Emergency Grant form state
  const [sosId, setSosId] = useState<string>('');
  const [selectedResponderId, setSelectedResponderId] = useState<string>('');
  const [grantIdToRevoke, setGrantIdToRevoke] = useState<string>('');

  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [isGranting, setIsGranting] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  const fetchTransactions = async () => {
    try {
      const [txs, resp] = await Promise.allSettled([
        blockchainApi.listTransactions(20),
        systemApi.listResponders(),
      ]);
      if (txs.status === 'fulfilled') setTransactions(txs.value);
      if (resp.status === 'fulfilled') {
        setResponders(resp.value);
        if (resp.value.length > 0 && !selectedResponderId) {
          setSelectedResponderId(resp.value[0].id);
        }
      }
    } catch (err) {
      console.warn('Failed to load blockchain transactions', err);
    }
  };

  useEffect(() => {
    fetchTransactions();
  }, []);

  const handleRegisterIdentity = async () => {
    setIsLoading(true);
    setError(null);
    setSuccessMsg(null);
    try {
      const res = await blockchainApi.registerIdentity();
      setRegisterResult(res);
      setSuccessMsg(
        res.success
          ? `Identity registered on smart contract! TX: ${res.tx_hash || 'OK'}`
          : `Registration response: ${res.error || 'Done'}`
      );
      await refreshProfile();
      await fetchTransactions();
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setIsLoading(false);
    }
  };

  const handleVerifyIdentity = async () => {
    if (!user?.id) {
      setError('Please sign in to verify your identity on chain.');
      return;
    }
    setIsLoading(true);
    setError(null);
    try {
      const res = await blockchainApi.verifyIdentity(user.id);
      setVerifyStatus(res.blockchain_registered);
      setSuccessMsg(`On-chain verification check: ${res.blockchain_registered ? 'CONFIRMED' : 'NOT FOUND'}`);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setIsLoading(false);
    }
  };

  const handleGrantAccess = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!sosId || !selectedResponderId) {
      setError('Both SOS Event ID and Responder ID are required to grant access.');
      return;
    }
    setIsGranting(true);
    setError(null);
    setSuccessMsg(null);
    try {
      const res = await blockchainApi.grantEmergencyAccess(sosId, selectedResponderId);
      setGrantIdToRevoke(res.grant_id);
      setSuccessMsg(`Emergency access granted on blockchain! Grant ID: ${res.grant_id}`);
      await fetchTransactions();
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setIsGranting(false);
    }
  };

  const handleRevokeAccess = async () => {
    if (!grantIdToRevoke) {
      setError('Please enter a Grant ID to revoke access.');
      return;
    }
    setIsGranting(true);
    setError(null);
    try {
      await blockchainApi.revokeEmergencyAccess(grantIdToRevoke);
      setSuccessMsg(`Emergency access revoked on blockchain for grant ${grantIdToRevoke}`);
      await fetchTransactions();
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setIsGranting(false);
    }
  };

  const txColumns: Column<BlockchainTxResponse>[] = [
    { header: 'Type', accessor: (t) => <strong>{t.tx_type}</strong> },
    {
      header: 'Transaction Hash',
      accessor: (t) => <span className="mono" style={{ fontSize: '11px' }}>{t.tx_hash ? `${t.tx_hash.substring(0, 18)}...` : '—'}</span>,
    },
    { header: 'Status', accessor: (t) => <StatusBadge status={t.status} size="sm" /> },
    { header: 'Latency', accessor: (t) => (t.latency_ms != null ? `${t.latency_ms.toFixed(1)} ms` : '—') },
  ];

  return (
    <div>
      <PageHeader
        title="Blockchain Identity & Emergency Access"
        subtitle="Cryptographic verification and smart contract access delegation"
        actions={
          <Button size="sm" icon={<RefreshCw size={14} />} onClick={fetchTransactions}>
            Refresh Ledger
          </Button>
        }
      />

      <ErrorMessage error={error} onDismiss={() => setError(null)} />
      {successMsg && <MessageBanner type="success" message={successMsg} onDismiss={() => setSuccessMsg(null)} />}

      <div className="metrics-grid">
        <MetricCard
          label="Identity Registration"
          value={user?.blockchain_registered ? 'REGISTERED' : 'UNREGISTERED'}
          badge={<StatusBadge status={user?.blockchain_registered ? 'ACTIVE' : 'NOT_RUN'} />}
          desc={user?.blockchain_registered ? 'Verified on Smart Contract' : 'Not registered on blockchain'}
          icon={<ShieldCheck size={18} />}
        />

        <MetricCard
          label="On-Chain Status"
          value={verifyStatus === null ? 'Not Checked' : verifyStatus ? 'VERIFIED' : 'UNVERIFIED'}
          desc={user?.id ? `User UUID: ${user.id.substring(0, 8)}...` : 'Sign in to check'}
          icon={<Key size={18} />}
        />

        <MetricCard
          label="Ledger Transactions"
          value={transactions.length}
          desc="Recent smart contract interactions"
          icon={<Cpu size={18} />}
        />
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20 }}>
        {/* Identity Registration & Verification */}
        <Card title="Identity Management" subtitle="Call smart contract registration method" icon={<FileCheck size={16} />}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
            <div style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>
              Registers a SHA-256 canonical hash of the tourist's verified identity credentials on the blockchain contract.
            </div>

            <div style={{ display: 'flex', gap: 10 }}>
              <Button
                variant="primary"
                onClick={handleRegisterIdentity}
                isLoading={isLoading}
                icon={<Lock size={15} />}
                style={{ flex: 1 }}
              >
                Register My Identity
              </Button>
              <Button
                onClick={handleVerifyIdentity}
                isLoading={isLoading}
                icon={<CheckCircle size={15} />}
                style={{ flex: 1 }}
              >
                Verify on Chain
              </Button>
            </div>

            {registerResult && (
              <div className="code-block" style={{ fontSize: '11.5px' }}>
                <div><strong>Success:</strong> {registerResult.success ? 'True' : 'False'}</div>
                {registerResult.tx_hash && <div><strong>TX Hash:</strong> {registerResult.tx_hash}</div>}
                {registerResult.block_number && <div><strong>Block:</strong> {registerResult.block_number}</div>}
                {registerResult.gas_used && <div><strong>Gas Used:</strong> {registerResult.gas_used}</div>}
                <div><strong>Latency:</strong> {registerResult.latency_ms.toFixed(1)} ms</div>
                {registerResult.identity_hash && <div><strong>Hash:</strong> {registerResult.identity_hash}</div>}
              </div>
            )}
          </div>
        </Card>

        {/* Emergency Access Delegation */}
        <Card title="Emergency Access Control" subtitle="Grant & revoke medical/location access to responders" icon={<Key size={16} />}>
          <form onSubmit={handleGrantAccess}>
            <Input
              label="SOS Event UUID *"
              value={sosId}
              onChange={(e) => setSosId(e.target.value)}
              placeholder="e.g. SOS UUID from emergency page"
              required
            />

            <div className="form-group">
              <label className="form-label">Select Authorized Responder *</label>
              <select
                className="form-select"
                value={selectedResponderId}
                onChange={(e) => setSelectedResponderId(e.target.value)}
                required
              >
                <option value="">Select a responder...</option>
                {responders.map((r) => (
                  <option key={r.id} value={r.id}>
                    {r.organization} ({r.id.substring(0, 8)}...)
                  </option>
                ))}
              </select>
            </div>

            <Button
              type="submit"
              variant="primary"
              isLoading={isGranting}
              icon={<Key size={15} />}
              style={{ width: '100%', marginBottom: 12 }}
            >
              Grant Emergency Access on Blockchain
            </Button>
          </form>

          <div style={{ paddingTop: 12, borderTop: '1px solid var(--border-subtle)' }}>
            <div className="form-group">
              <label className="form-label">Grant ID to Revoke</label>
              <div style={{ display: 'flex', gap: 8 }}>
                <input
                  type="text"
                  className="form-input"
                  value={grantIdToRevoke}
                  onChange={(e) => setGrantIdToRevoke(e.target.value)}
                  placeholder="Grant UUID"
                />
                <Button variant="danger" size="sm" onClick={handleRevokeAccess} disabled={!grantIdToRevoke || isGranting}>
                  <Unlock size={14} /> Revoke
                </Button>
              </div>
            </div>
          </div>
        </Card>
      </div>

      {/* Transaction History */}
      <div style={{ marginTop: 20 }}>
        <Card title="Blockchain Transaction Ledger" subtitle="Queried from GET /api/v1/blockchain/transactions">
          <DataTable
            columns={txColumns}
            data={transactions}
            keyExtractor={(t) => t.id}
            emptyMessage="No blockchain transactions recorded in database."
          />
        </Card>
      </div>
    </div>
  );
};
