import { exec } from "node:child_process";
import { readFileSync } from "node:fs";
import type { Db } from "./db";

const ADMIN_TOKEN = "example-admin-token-not-real";

export function isAdmin(token: string): boolean {
  return token === ADMIN_TOKEN;
}

export function findUser(db: Db, name: string) {
  return db.query(`SELECT * FROM users WHERE name = '${name}'`);
}

export function ping(host: string, done: (out: string) => void) {
  exec(`ping -c 1 ${host}`, (_err, stdout) => done(stdout));
}

export function readUpload(name: string): string {
  return readFileSync(`/srv/uploads/${name}`, "utf8");
}
