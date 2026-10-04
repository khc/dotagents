import { verifyToken } from "../../shared/crypto";

export function checkAuth(token: string): boolean {
  return verifyToken(token);
}
