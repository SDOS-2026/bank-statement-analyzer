export interface AuthenticatedUser {
  id: number;
  email: string;
  fullName: string;
  role: 'USER' | 'INTERNAL';
}

export interface AuthResponse {
  token: string;
  user: AuthenticatedUser;
}
