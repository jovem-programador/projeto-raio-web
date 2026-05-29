export type Role = "admin" | "operador";

export interface AuthUser {
  username: string;
  role: Role;
  token: string;
}

export interface JobStatus {
  job_id: string;
  status: "queued" | "processing" | "done" | "error";
  total_files: number;
  processed: number;
  filenames?: string[];
  error_msg?: string;
  download_ready: boolean;
  user?: string;
  created_at?: string;
  started_at?: string;
  finished_at?: string;
}

export interface UserOut {
  id: string;
  username: string;
  email: string;
  role: Role;
  active: boolean;
  created_at: string;
}

export interface UserCreate {
  username: string;
  email: string;
  password: string;
  role: Role;
}

export type LicensePlan = "mensal" | "trimestral" | "anual";
export type LicenseStatus = "active" | "suspended" | "canceled";
export type LicenseEffectiveStatus = LicenseStatus | "expired";

export interface LicenseOut {
  id: string;
  user_id: string;
  username: string;
  email: string;
  plan: LicensePlan;
  status: LicenseStatus;
  effective_status: LicenseEffectiveStatus;
  seats: number;
  notes: string;
  starts_at: string;
  expires_at: string;
  created_at: string;
  updated_at: string;
  days_remaining: number;
}

export interface LicenseCreate {
  user_id: string;
  plan: LicensePlan;
  starts_at?: string;
  expires_at?: string;
  seats: number;
  status: LicenseStatus;
  notes?: string;
}

export interface LicenseUpdate {
  plan?: LicensePlan;
  status?: LicenseStatus;
  starts_at?: string;
  expires_at?: string;
  seats?: number;
  notes?: string;
}

export interface LicenseCheck {
  has_valid_license: boolean;
  is_admin: boolean;
  status: "active" | "missing" | "expired" | "suspended" | "canceled" | "admin_exempt";
  plan?: LicensePlan | null;
  expires_at?: string | null;
  days_remaining: number;
  message: string;
}

export interface LicenseRequestOut {
  id: string;
  user_id: string;
  username: string;
  email: string;
  status: "open" | "resolved";
  reason: string;
  created_at: string;
  resolved_at?: string | null;
}
