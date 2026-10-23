import jwt from "jsonwebtoken";

export function claims(token: string, key: string) {
  return jwt.verify(token, key);
}
