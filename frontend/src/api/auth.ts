import { apiGet, apiPost } from "./client";

export interface TokenResponse {
  access_token: string;
  token_type: string;
}

export interface CurrentUser {
  id: string;
  email: string;
  name: string;
}

export const register = (email: string, password: string, name: string) =>
  apiPost<TokenResponse>("/auth/register", { email, password, name });

export const login = (email: string, password: string) => apiPost<TokenResponse>("/auth/login", { email, password });

export const me = () => apiGet<CurrentUser>("/auth/me");
