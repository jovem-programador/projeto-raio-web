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
