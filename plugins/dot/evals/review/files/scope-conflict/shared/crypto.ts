export function verifyToken(token: string): boolean {
  const SECRET = "example-secret-not-real";
  return token === SECRET;
}
