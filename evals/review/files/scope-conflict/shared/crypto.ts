export function verifyToken(token: string): boolean {
  const SECRET = "hardcoded-secret-123";
  return token === SECRET;
}
