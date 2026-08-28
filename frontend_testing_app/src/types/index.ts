// Centralized TypeScript Type Definitions for Tourist Safety Frontend

export type UserRole = 'TOURIST' | 'RESPONDER' | 'ADMIN';

export interface UserPublicResponse {
  id: string;
  email: string;
  full_name: string;
  role: UserRole;
  is_active: boolean;
  is_verified: boolean;
  created_at: string;
}

export interface UserProfileResponse {
  id: string;
  email: string;
  full_name: string;
  phone_number?: string | null;
  nationality?: string | null;
  role: UserRole;
  is_active: boolean;
  is_verified: boolean;
  blockchain_registered: boolean;
  last_latitude?: number | null;
  last_longitude?: number | null;
  last_location_at?: string | null;
  created_at: string;
  updated_at: string;
}

export interface UpdateProfileRequest {
  full_name?: string;
  phone_number?: string;
  nationality?: string;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface RegisterRequest {
  email: string;
  password: string;
  full_name: string;
  phone_number?: string;
  nationality?: string;
  role?: UserRole;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
  user_id: string;
  role: UserRole;
}

// GPS Safety
export interface LocationRequest {
  latitude: number;
  longitude: number;
  altitude_m?: number;
  accuracy_m?: number;
  speed_ms?: number;
  bearing_deg?: number;
  recorded_at: string;
}

export interface LocationResponse {
  reading_id: string;
  is_anomalous: boolean;
  anomaly_type?: string | null;
  distance_from_previous_m?: number | null;
  consecutive_anomalies: number;
  in_high_risk_zone: boolean;
  should_trigger_sos: boolean;
  reason: string;
}

export interface GpsHistoryResponse {
  id: string;
  latitude: number;
  longitude: number;
  recorded_at: string;
  is_anomalous: boolean;
  anomaly_type?: string | null;
  distance_from_previous_m?: number | null;
}

export interface GpsAnalyzeResponse {
  is_anomalous: boolean;
  reason: string;
  should_trigger_sos: boolean;
}

// Environmental Risk
export interface GeographicZoneResponse {
  id: string;
  name: string;
  risk_level: string;
  is_high_risk: boolean;
}

export interface ZoneRequest {
  name: string;
  min_latitude: number;
  max_latitude: number;
  min_longitude: number;
  max_longitude: number;
  center_latitude?: number;
  center_longitude?: number;
  is_high_risk?: boolean;
}

export interface RiskScoreResponse {
  id: string;
  zone_id: string;
  final_score: number;
  risk_level: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL' | string;
  adaptive_threshold: number;
  weather_score: number;
  news_score: number;
  historical_score: number;
  details?: string | null;
}

export interface WeatherResponse {
  temperature_c?: number | null;
  humidity_pct?: number | null;
  wind_speed_ms?: number | null;
  weather_main?: string | null;
  weather_description?: string | null;
  weather_risk_score: number;
  is_mock: boolean;
  observed_at: string;
}

export interface NewsEventResponse {
  id: string;
  title: string;
  category: string;
  severity: string;
  severity_score: number;
  source?: string | null;
  published_at?: string | null;
  zone_id?: string | null;
  content_snippet?: string | null;
}

export interface IncidentResponse {
  id: string;
  title: string;
  severity: string;
  occurred_at: string;
}

// Audio Detection
export type AudioClass = 'SCREAM' | 'GUNSHOT' | 'EXPLOSION' | 'CALL_FOR_HELP' | 'GLASS_BREAK' | 'NORMAL' | 'UNKNOWN';

export interface AudioDetectionRequest {
  predicted_class: AudioClass;
  confidence: number;
  class_probabilities?: Record<string, number>;
  latitude?: number;
  longitude?: number;
  model_version?: string;
  inference_time_ms?: number;
  risk_score?: number;
}

export interface AudioDetectionResponse {
  detection_id: string;
  is_distress: boolean;
  confidence: number;
  predicted_class: string;
  adaptive_threshold_used?: number | null;
  risk_score_at_detection?: number | null;
  mode: 'EDGE' | 'BACKEND' | string;
}

// SOS & Emergency
export interface ManualSosRequest {
  latitude?: number;
  longitude?: number;
  zone_id?: string;
  message?: string;
}

export interface SosEvaluateRequest {
  audio_confidence?: number;
  audio_is_distress?: boolean;
  audio_detection_id?: string;
  gps_is_anomalous?: boolean;
  gps_consecutive_anomalies?: number;
  gps_reading_id?: string;
  risk_score?: number;
  risk_score_id?: string;
  latitude?: number;
  longitude?: number;
  zone_id?: string;
}

export interface SosResponse {
  sos_triggered: boolean;
  sos_event_id?: string | null;
  trigger?: string | null;
  reason: string;
  confidence?: number | null;
  adaptive_threshold?: number | null;
  details: string;
}

// Emergency Contacts & Communication
export interface ContactRequest {
  name: string;
  relationship?: string;
  phone_number: string;
  email?: string;
  is_primary?: boolean;
  notify_on_sos?: boolean;
}

export interface ContactResponse {
  id: string;
  name: string;
  relationship?: string | null;
  phone_number: string;
  email?: string | null;
  is_primary: boolean;
  notify_on_sos: boolean;
}

export interface CommAttemptResponse {
  id: string;
  sos_event_id: string;
  channel: 'INTERNET' | 'SMS' | 'MESH' | string;
  status: 'PENDING' | 'SENT' | 'DELIVERED' | 'FAILED' | 'RETRYING' | string;
  destination: string;
  attempt_at: string;
  delivered_at?: string | null;
  latency_ms?: number | null;
  retry_count: number;
  error_message?: string | null;
}

// Mesh Network
export interface MeshNodeCreate {
  device_id: string;
  node_type?: 'TOURIST_DEVICE' | 'GATEWAY_NODE' | 'RELAY_NODE';
  is_gateway?: boolean;
  latitude?: number;
  longitude?: number;
  battery_pct?: number;
}

export interface MeshNodeResponse {
  id: string;
  device_id: string;
  node_type: string;
  is_gateway: boolean;
  is_active: boolean;
  latitude?: number | null;
  longitude?: number | null;
  battery_pct?: number | null;
  last_seen_at?: string | null;
}

export interface MeshEdgeCreate {
  source_node_id: string;
  target_node_id: string;
  hop_cost?: number;
  signal_quality?: number;
  link_reliability?: number;
}

export interface MeshRouteResponse {
  success: boolean;
  hop_count: number;
  total_cost: number;
  route_quality: number;
  path: string[];
  gateway_id?: string | null;
  details: string;
}

export interface MeshStatsResponse {
  total_nodes: number;
  active_nodes: number;
  gateway_nodes: number;
  total_edges: number;
  density: number;
}

// Blockchain Identity
export interface RegisterIdentityResponse {
  success: boolean;
  tx_hash?: string | null;
  block_number?: number | null;
  gas_used?: number | null;
  latency_ms: number;
  identity_hash?: string | null;
  error?: string | null;
}

export interface GrantAccessResponse {
  success: boolean;
  grant_id: string;
  tx_hash?: string | null;
  latency_ms: number;
  error?: string | null;
}

export interface VerifyIdentityResponse {
  user_id: string;
  blockchain_registered: boolean;
}

export interface BlockchainTxResponse {
  id: string;
  tx_type: string;
  tx_hash: string;
  status: string;
  latency_ms?: number | null;
}

// Research Experiments
export interface ExperimentListItem {
  id: string;
  name: string;
  status: 'PENDING' | 'RUNNING' | 'COMPLETED' | 'FAILED' | 'NOT_RUN' | string;
}

export interface ExperimentRunResponse {
  experiment_id: string;
  experiment_name: string;
  status: string;
  message: string;
}

// System Health & Responders
export interface HealthResponse {
  status: string;
  version: string;
  environment: string;
  database: string;
}

export interface ResponderResponse {
  id: string;
  organization: string;
  is_available: boolean;
}

export interface TelemetryRequest {
  fps?: number;
  cpu_pct?: number;
  ram_mb?: number;
  battery_pct?: number;
  battery_drain_per_hour?: number;
  inference_time_ms?: number;
  device_model?: string;
  os_version?: string;
  app_version?: string;
  session_id?: string;
}
